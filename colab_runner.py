# =====================================================================
# 1-CLICK ALL-IN-ONE GOOGLE COLAB PRO SERVER
# Copy and paste this ENTIRE block into a single Colab cell and press Run (Shift + Enter)
# =====================================================================

# 1. Mount Google Drive for persistent model storage
from google.colab import drive
import os, io, base64, threading
from typing import Optional

drive.mount('/content/drive')
drive_cache_dir = '/content/drive/MyDrive/colab_model_cache'
os.makedirs(drive_cache_dir, exist_ok=True)
os.environ['HF_HOME'] = drive_cache_dir

# 2. Install dependencies
!pip install -q transformers accelerate bitsandbytes torchvision qwen-vl-utils fastapi uvicorn pycloudflared pydantic pillow

# 3. Load Multimodal Model on GPU (A100 / L4 / T4)
import torch
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig
from PIL import Image
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn
from pycloudflared import try_cloudflare
from qwen_vl_utils import process_vision_info
from transformers import TextIteratorStreamer

MODEL_ID = "huihui-ai/Qwen2.5-VL-7B-Instruct-abliterated"
print(f"Loading {MODEL_ID} into Colab GPU...")

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True
)

processor = AutoProcessor.from_pretrained(MODEL_ID, cache_dir=drive_cache_dir)
model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
    MODEL_ID,
    quantization_config=bnb_config,
    device_map="auto",
    cache_dir=drive_cache_dir
)
print("Model loaded successfully into GPU!")

# 4. FastAPI & Cloudflare Tunnel
app = FastAPI()

@app.get("/health")
def health():
    gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
    free_mem, total_mem = torch.cuda.mem_get_info() if torch.cuda.is_available() else (0, 0)
    return {
        "status": "online",
        "gpu": gpu_name,
        "vram_free_gb": round(free_mem / (1024**3), 2),
        "vram_total_gb": round(total_mem / (1024**3), 2)
    }

class Query(BaseModel):
    prompt: str
    image_base64: Optional[str] = None
    image_url: Optional[str] = None
    max_tokens: int = 1024

def prepare_messages(q: Query):
    content = []
    if q.image_base64:
        img_data = base64.b64decode(q.image_base64)
        image = Image.open(io.BytesIO(img_data)).convert("RGB")
        content.append({"type": "image", "image": image})
    elif q.image_url:
        content.append({"type": "image", "image": q.image_url})
    content.append({"type": "text", "text": q.prompt})
    return [{"role": "user", "content": content}]

@app.post("/generate")
def generate(q: Query):
    messages = prepare_messages(q)
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    image_inputs, video_inputs = process_vision_info(messages)
    inputs = processor(text=[text], images=image_inputs, videos=video_inputs, padding=True, return_tensors="pt").to("cuda")
    with torch.no_grad():
        generated_ids = model.generate(**inputs, max_new_tokens=q.max_tokens)
        generated_ids_trimmed = [out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)]
        output_text = processor.batch_decode(generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)
    return {"response": output_text[0]}

@app.post("/stream")
def stream(q: Query):
    messages = prepare_messages(q)
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    image_inputs, video_inputs = process_vision_info(messages)
    inputs = processor(text=[text], images=image_inputs, videos=video_inputs, padding=True, return_tensors="pt").to("cuda")
    streamer = TextIteratorStreamer(processor.tokenizer, skip_prompt=True, skip_special_tokens=True)
    generation_kwargs = dict(inputs, streamer=streamer, max_new_tokens=q.max_tokens)
    threading.Thread(target=model.generate, kwargs=generation_kwargs).start()
    def event_stream():
        for new_text in streamer:
            yield new_text
    return StreamingResponse(event_stream(), media_type="text/plain")

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8000)

threading.Thread(target=run_server, daemon=True).start()
public_url = try_cloudflare(port=8000)
print("\n" + "="*60)
print(f"YOUR TUNNEL URL: {public_url.tunnel}")
print("="*60)
