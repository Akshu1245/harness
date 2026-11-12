import os
from dotenv import load_dotenv
import requests
from openai import OpenAI

load_dotenv()

APINEX_BASE_URL = "https://api.apinex.bond/v1"
APINEX_API_KEY = os.environ.get("APINEX_API_KEY")

def get_client():
    if not APINEX_API_KEY:
        raise ValueError("APINEX_API_KEY environment variable is not set.")
    return OpenAI(
        base_url=APINEX_BASE_URL,
        api_key=APINEX_API_KEY,
    )

def chat(model: str, prompt: str, system: str = None) -> str:
    """Send a chat completion to APInex."""
    client = get_client()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    
    response = client.chat.completions.create(
        model=model,
        messages=messages,
    )
    return response.choices[0].message.content

def make_decision(state: str, questions: dict, model: str = "free/jev-1.13") -> dict:
    """Ask Jev Decision models typed questions and receive calibrated probabilities and scores.
    
    Supported question types:
      - noul: Binary yes/no returning probability 0.0 - 1.0.
      - choice: Multi-class selection with 'criteria' dict {option: description}.
      - score: Ordered grading scale with 'criteria' list of ordered levels.
    """
    if not APINEX_API_KEY:
        raise ValueError("APINEX_API_KEY environment variable is not set.")
    
    url = f"{APINEX_BASE_URL}/decisions"
    headers = {
        "Authorization": f"Bearer {APINEX_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "state": state,
        "questions": questions,
    }
    res = requests.post(url, headers=headers, json=payload, timeout=15)
    res.raise_for_status()
    return res.json()

def web_search(query: str, count: int = 5) -> dict:
    """Perform a live web search using APInex Web Search tool."""
    if not APINEX_API_KEY:
        raise ValueError("APINEX_API_KEY environment variable is not set.")
    
    url = f"{APINEX_BASE_URL}/tools/web/search"
    headers = {
        "Authorization": f"Bearer {APINEX_API_KEY}",
        "Content-Type": "application/json",
    }
    res = requests.post(url, headers=headers, json={"query": query, "count": count}, timeout=15)
    res.raise_for_status()
    return res.json()

if __name__ == "__main__":
    print("Testing Jev 1.13 Decision Model on APInex...")
    state = "We are selecting the backend database for an autonomous agent task routing platform."
    questions = {
        "best_db": {
            "type": "choice",
            "instructions": "Which database is optimal for low-latency job queues and state storage?",
            "criteria": {
                "redis": "In-memory key-value store with Pub/Sub and Streams",
                "postgres": "Relational SQL database with JSONB and transactional guarantees",
                "mongodb": "Document-oriented NoSQL database"
            }
        },
        "needs_caching_layer": {
            "type": "noul",
            "instructions": "Will this architecture strictly require a dedicated caching layer?"
        }
    }
    decision = make_decision(state, questions)
    print("Decision output:")
    for q_name, q_res in decision.get("answers", {}).items():
        print(f"  [{q_name}]: {q_res}")
