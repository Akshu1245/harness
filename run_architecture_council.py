import os
import json
import concurrent.futures
from dotenv import load_dotenv
from openai import OpenAI
import requests

load_dotenv()

RESPAN_KEY = os.environ.get("RESPAN_API_KEY")
EXPLABS_KEY = os.environ.get("EXPLABS_API_KEY")
APINEX_KEY = os.environ.get("APINEX_API_KEY")

respan_client = OpenAI(base_url="https://gateway.respan.ai/v1", api_key=RESPAN_KEY)
explabs_client = OpenAI(base_url="https://api.experientiallabs.ai/v1", api_key=EXPLABS_KEY)
apinex_client = OpenAI(base_url="https://api.apinex.bond/v1", api_key=APINEX_KEY)

# 1. Jev Decision on core architecture questions
def run_jev_decisions():
    url = "https://api.apinex.bond/v1/decisions"
    headers = {"Authorization": f"Bearer {APINEX_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "free/jev-1.13",
        "state": "Designing RakshEx: A multi-agent AI coding & execution platform managing 16 LLMs, real-time code verification, persistent caching, and async execution.",
        "questions": {
            "core_framework": {
                "type": "choice",
                "instructions": "Which Python backend framework is optimal for high-concurrency async LLM dispatch and WebSocket streaming?",
                "criteria": {
                    "fastapi": "Asynchronous FastAPI with Uvicorn and Pydantic V2",
                    "django_ninja": "Django Ninja with async ORM",
                    "flask_gevent": "Flask with WSGI/Gevent"
                }
            },
            "job_state_store": {
                "type": "choice",
                "instructions": "Which message broker & state store is best suited for job checkpointing?",
                "criteria": {
                    "redis_streams": "Redis Streams / Dragonfly in-memory message bus",
                    "rabbitmq": "RabbitMQ AMQP message broker",
                    "kafka": "Apache Kafka event streaming"
                }
            },
            "orchestrator_pattern": {
                "type": "choice",
                "instructions": "Which agentic orchestration pattern is most reliable for production?",
                "criteria": {
                    "deterministic_graph": "Two-level directed acyclic graph with explicit state machine transitions",
                    "autonomous_swarm": "Unconstrained peer-to-peer agent chat loops",
                    "hierarchical_subagents": "Multi-layer recursive subagent trees"
                }
            }
        }
    }
    r = requests.post(url, headers=headers, json=payload, timeout=20)
    return r.json()

# 2. Query individual models on their designated specialization
tasks = {
    "Gemini 4 Carbon": {
        "client": respan_client,
        "model": "respan/gemini-4-carbon:free",
        "prompt": "You are Lead Reasoning Architect. In 3 concise bullet points, provide the formal architectural blueprint for RakshEx (state machine graph, fault tolerance, and zero-hallucination verification pipeline)."
    },
    "Claude Fable 5.2": {
        "client": explabs_client,
        "model": "claude-fable-5.2:free",
        "prompt": "You are Principal Systems Architect. In 3 concise bullet points, design the multi-agent task execution and checkpoint resume protocol for RakshEx when external API rate limits or failures occur."
    },
    "Qwen 3.8 MAX": {
        "client": apinex_client,
        "model": "free/qwen-3.8-max",
        "prompt": "You are Principal Backend Engineer. In 3 concise bullet points, specify the exact FastAPI async worker architecture, thread/process pool strategy, and streaming endpoint design for RakshEx."
    },
    "DeepSeek V4 Pro": {
        "client": apinex_client,
        "model": "free/deepseek-v4-pro-0813",
        "prompt": "You are Principal Security & Code Auditor. In 3 concise bullet points, identify the 3 most dangerous architectural bottlenecks or vulnerabilities in multi-agent LLM systems and how RakshEx must eliminate them."
    },
    "Kimi K3": {
        "client": apinex_client,
        "model": "free/kimi-k3",
        "prompt": "You are Context & Memory Specialist. In 3 concise bullet points, design the long-term context compression and caching strategy for RakshEx across 1M-token sessions."
    },
    "GPT-6 Luna": {
        "client": apinex_client,
        "model": "free/gpt-6-luna",
        "prompt": "You are API Contract & Developer Experience Lead. In 3 concise bullet points, design the clean client interface and SDK developer experience for RakshEx."
    }
}

def query_model(name, cfg):
    try:
        resp = cfg["client"].chat.completions.create(
            model=cfg["model"],
            messages=[{"role": "user", "content": cfg["prompt"]}],
            max_tokens=250,
            timeout=30,
        )
        return name, resp.choices[0].message.content.strip()
    except Exception as e:
        return name, f"Error: {e}"

print("Running Jev 1.13 architectural decisions...")
jev_results = run_jev_decisions()

print("Querying specialized frontier models in parallel...")
model_responses = {}
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
    futures = {executor.submit(query_model, name, cfg): name for name, cfg in tasks.items()}
    for f in concurrent.futures.as_completed(futures):
        name, output = f.result()
        model_responses[name] = output

# Output compiled report
output_data = {
    "jev_decisions": jev_results.get("answers", {}),
    "model_proposals": model_responses
}

with open("d:\\unreseted ai\\architecture_council_report.json", "w") as f:
    json.dump(output_data, f, indent=2)

print("\n--- ARCHITECTURE COUNCIL CONSULTATION COMPLETE ---")
