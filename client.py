import argparse
import base64
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
import requests

CONFIG_FILE = os.path.join(os.path.dirname(__file__), ".colab_config.json")

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                if "endpoints" not in data:
                    data["endpoints"] = [data["endpoint"]] if "endpoint" in data else []
                if "current_index" not in data:
                    data["current_index"] = 0
                return data
        except Exception:
            return {"endpoints": [], "current_index": 0}
    return {"endpoints": [], "current_index": 0}

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

def add_endpoint(url):
    url = url.strip().rstrip("/")
    config = load_config()
    endpoints = config.get("endpoints", [])
    if url not in endpoints:
        endpoints.append(url)
        config["endpoints"] = endpoints
        save_config(config)
        print(f"[OK] Added Colab Worker: {url}")
        print(f"Total active workers registered: {len(endpoints)}")
    else:
        print(f"[INFO] Endpoint already in pool: {url}")

def remove_endpoint(url):
    url = url.strip().rstrip("/")
    config = load_config()
    endpoints = config.get("endpoints", [])
    if url in endpoints:
        endpoints.remove(url)
        config["endpoints"] = endpoints
        save_config(config)
        print(f"[OK] Removed worker: {url}")
    else:
        print(f"[WARN] Endpoint not found: {url}")

def check_worker_status(url):
    try:
        r = requests.get(f"{url}/health", timeout=6)
        if r.status_code == 200:
            data = r.json()
            return {
                "url": url,
                "online": True,
                "gpu": data.get("gpu", "GPU Active"),
                "vram_free": data.get("vram_free_gb", "N/A"),
                "vram_total": data.get("vram_total_gb", "N/A")
            }
    except Exception:
        pass

    # Fallback check
    try:
        r = requests.get(f"{url}/docs", timeout=5)
        if r.status_code == 200:
            return {"url": url, "online": True, "gpu": "Active (Legacy endpoint)", "vram_free": "N/A", "vram_total": "N/A"}
    except Exception:
        pass

    return {"url": url, "online": False, "gpu": "Unreachable", "vram_free": "-", "vram_total": "-"}

def list_status():
    config = load_config()
    endpoints = config.get("endpoints", [])
    if not endpoints:
        print("\nNo Colab workers configured in your cluster pool.")
        print("Add accounts using: colab --add-url <tunnel_url>\n")
        return

    print("\n[+] Probing health and GPU telemetry across all registered accounts...")
    with ThreadPoolExecutor(max_workers=max(1, len(endpoints))) as executor:
        results = list(executor.map(check_worker_status, endpoints))

    print("\n" + "="*85)
    print(f"{'#':<3} {'Worker Tunnel':<36} {'GPU Hardware':<22} {'VRAM Free':<12} {'Status':<10}")
    print("="*85)
    for idx, r in enumerate(results, 1):
        status_str = "[ONLINE]" if r["online"] else "[OFFLINE]"
        vram_str = f"{r['vram_free']}/{r['vram_total']} GB" if r['vram_free'] != "-" else "-"
        print(f"{idx:<3} {r['url']:<36} {r['gpu'][:21]:<22} {vram_str:<12} {status_str:<10}")
    print("="*85 + "\n")

def get_next_healthy_endpoint():
    config = load_config()
    endpoints = config.get("endpoints", [])
    if not endpoints:
        return None

    start_idx = config.get("current_index", 0)
    n = len(endpoints)

    for i in range(n):
        idx = (start_idx + i) % n
        url = endpoints[idx]
        info = check_worker_status(url)
        if info["online"]:
            config["current_index"] = (idx + 1) % n
            save_config(config)
            return url

    return endpoints[0]

def encode_image(image_path):
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")

def query_model(prompt, image_path=None, stream=True):
    endpoint = get_next_healthy_endpoint()
    if not endpoint:
        print("\nError: No Colab accounts configured in your pool.")
        print("Add accounts using: colab --add-url <tunnel_url>\n")
        return

    payload = {"prompt": prompt}
    if image_path:
        if image_path.startswith("http://") or image_path.startswith("https://"):
            payload["image_url"] = image_path
        else:
            try:
                payload["image_base64"] = encode_image(image_path)
            except Exception as e:
                print(f"Error reading image: {e}")
                return

    print(f"[Coordinator -> Dispatching job to Colab Worker: {endpoint}]")

    if stream:
        url = f"{endpoint}/stream"
        try:
            with requests.post(url, json=payload, stream=True, timeout=180) as r:
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=None, decode_unicode=True):
                    if chunk:
                        sys.stdout.write(chunk)
                        sys.stdout.flush()
                print()
        except requests.exceptions.RequestException:
            url = f"{endpoint}/generate"
            try:
                response = requests.post(url, json=payload, timeout=180)
                response.raise_for_status()
                data = response.json()
                print(data.get("response", ""))
            except requests.exceptions.RequestException as e:
                print(f"\n[FAILOVER TRIGGERED] Worker {endpoint} failed: {e}")
                print("Checking next available worker in pool...")
    else:
        url = f"{endpoint}/generate"
        try:
            response = requests.post(url, json=payload, timeout=180)
            response.raise_for_status()
            data = response.json()
            print(data.get("response", ""))
        except requests.exceptions.RequestException as e:
            print(f"Worker {endpoint} failed: {e}")

def chat_mode():
    config = load_config()
    endpoints = config.get("endpoints", [])
    if not endpoints:
        print("\nError: No Colab accounts configured in your pool.")
        print("Add them using: colab --add-url <tunnel_url>\n")
        return

    print(f"\n[Connected to Cluster Coordinator] Registered Workers: {len(endpoints)}")
    print("Commands:")
    print("  /image <path>  : Attach an image to your question")
    print("  /pool          : View live telemetry of all Colab workers")
    print("  exit / quit    : End chat session\n")

    current_image = None
    while True:
        try:
            prompt_prefix = f"[{os.path.basename(current_image)}] " if current_image else ""
            user_input = input(f"\nYou {prompt_prefix}> ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit"):
                break
            if user_input.lower() == "/pool":
                list_status()
                continue
            if user_input.startswith("/image "):
                img_p = user_input[7:].strip().strip('"').strip("'")
                if os.path.exists(img_p) or img_p.startswith("http"):
                    current_image = img_p
                    print(f"Image attached: {current_image}")
                else:
                    print(f"File not found: {img_p}")
                continue

            print("\nAI > ", end="")
            query_model(user_input, image_path=current_image, stream=True)
            current_image = None
        except (KeyboardInterrupt, EOFError):
            print("\nExiting chat.")
            break

def main():
    parser = argparse.ArgumentParser(description="Multi-Account Colab Pro Cluster & CLI Coordinator")
    parser.add_argument("--add-url", type=str, help="Add a Colab Pro account tunnel URL to the cluster pool")
    parser.add_argument("--remove-url", type=str, help="Remove a Colab account URL from the pool")
    parser.add_argument("--set-url", type=str, help="Set a single URL (or first account)")
    parser.add_argument("--status", action="store_true", help="Check health and connection status of all Colab accounts")
    parser.add_argument("--chat", action="store_true", help="Start interactive chat using the cluster pool")
    parser.add_argument("--image", type=str, help="Path to local image file or image URL to analyze")
    parser.add_argument("prompt", nargs="*", help="Direct prompt to send to the cluster")

    args = parser.parse_args()

    if args.add_url:
        add_endpoint(args.add_url)
        return

    if args.remove_url:
        remove_endpoint(args.remove_url)
        return

    if args.set_url:
        add_endpoint(args.set_url)
        return

    if args.status:
        list_status()
        return

    if args.chat:
        chat_mode()
        return

    if args.prompt:
        full_prompt = " ".join(args.prompt)
        query_model(full_prompt, image_path=args.image, stream=True)
        return

    parser.print_help()

if __name__ == "__main__":
    main()
