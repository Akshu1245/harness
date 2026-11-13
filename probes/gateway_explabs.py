import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.environ.get("EXPLABS_API_KEY")
if not api_key:
    raise ValueError("EXPLABS_API_KEY environment variable is not set. Please set it in your environment or .env file.")

# Initialize OpenAI-compatible client routed through Experiential Labs Gateway
client = OpenAI(
    base_url="https://api.experientiallabs.ai/v1",
    api_key=api_key,
)

if __name__ == "__main__":
    prompt = "Hello, who are you?"
    print(f"Sending prompt to Claude Fable 5.2 on Experiential Gateway...\n")
    
    # Minimal body: model + messages only
    response = client.chat.completions.create(
        model="claude-fable-5.2:free",  # Use "claude-fable-5.2" when paid credits are added
        messages=[{"role": "user", "content": prompt}],
    )
    
    print("Reply:")
    print(response.choices[0].message.content)
    print("\nToken Usage:")
    print(response.usage)
