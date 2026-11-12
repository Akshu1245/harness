# Rashi Harness · Multi-Agent Autonomous War Room & Loop Engineering Architecture

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%20Async-009688.svg)](https://fastapi.tiangolo.com/)
[![Models](https://img.shields.io/badge/Models-20%2B%20Frontier%20LLMs-indigo.svg)](#supported-models--providers)
[![Gateways](https://img.shields.io/badge/Gateways-OpenRouter%20%7C%20Free.ai%20%7C%20Respan%20%7C%20APInex%20%7C%20Langfuse-emerald.svg)](#supported-models--providers)

**Rashi Harness** is an enterprise-grade, decentralized autonomous loop engineering platform and visual war room that orchestrates 20+ frontier AI models into a self-healing, peer-reviewed execution network.

Instead of manual prompting, Rashi Harness implements **Loop Engineering**: you provide a single high-level goal, and the system autonomously searches open-source foundations, decomposes tasks, delegates across specialized models, runs adversarial peer-review debates, and enforces formal proof verification before writing code.

---

## 🌟 Key Features

1. **Zero-Prompt Autonomous Loop:**
   - Single goal input $\rightarrow$ automatic open-source GitHub discovery $\rightarrow$ architecture design $\rightarrow$ code generation $\rightarrow$ self-healing test loops.
2. **Adversarial Peer-Review Engine:**
   - Every builder model's proposal or code block is challenged by a rival adversarial auditor model (e.g. Qwen 3.8 MAX challenged by DeepSeek V4 Pro; Gemini 4 Carbon challenged by Claude Fable 5.2).
   - Builders must provide concrete code proofs, fencing tokens, or formal logic rather than handwaving.
3. **Probabilistic Decision Gate (Jev 1.13):**
   - ~300ms calibrated mathematical confidence scoring (`0.0` to `1.0`) evaluates architectural and deployment trade-offs.
4. **"Slack for AI Agents" Visual War Room:**
   - Real-time interactive dashboard ([`visual_war_room.html`](./visual_war_room.html)) tracking agent-to-agent debates, live telemetry, and memory states.
5. **Second Brain Memory Integration:**
   - Incorporates architectural patterns from `gbrain` (shared multi-agent memory) and `open-second-brain` (automatic rule evolution from peer rejections).
6. **Strict Budget & Circuit Breakers:**
   - Runs 100% on free-tier models across Respan, Experiential, and APInex.
   - Circuit breaker isolates paid gateway tools (e.g., Coarena's $5/day quota) strictly for critical deadlocks.

---

## 🏗️ System Architecture

```
                                [Client Goal]
                                      │
                                      ▼
             ┌──────────────────────────────────────────────────┐
             │ 1. OPEN-SOURCE DISCOVERY & GROUND TRUTH SEARCH   │
             │   (APInex Real-Time Web & GitHub Search Tool)    │
             └────────────────────────┬─────────────────────────┘
                                      │
                                      ▼
             ┌──────────────────────────────────────────────────┐
             │ 2. TIER 1: PROBABILISTIC DISPATCHER (Jev 1.13)   │
             │   (Sub-300ms Calibrated Route Evaluation)        │
             └────────────────────────┬─────────────────────────┘
                                      │
      ┌───────────────────────────────┼───────────────────────────────┐
      ▼                               ▼                               ▼
┌───────────────┐             ┌───────────────┐               ┌───────────────┐
│ TIER 2: DEEP  │             │ TIER 3: CODE  │               │ TIER 4: FAST  │
│ REASONING     │             │ & SCHEMAS     │               │ AGENT WORKERS │
│ - Gemini 4    │             │ - Qwen 3.8    │               │ - Muse Ember  │
│ - DeepSeek V4 │             │ - Kimi K3     │               │ - Gemini Flash│
│ - Claude Fable│             │ - GPT-6 Luna  │               │ - GLM Flash   │
└───────┬───────┘             └───────┬───────┘               └───────┬───────┘
        │                             │                               │
        └─────────────────────────────┼───────────────────────────────┘
                                      │
                                      ▼
             ┌──────────────────────────────────────────────────┐
             │ 3. ADVERSARIAL MODEL-VS-MODEL PEER REVIEW        │
             │   (Adversary attacks -> Builder defends -> Proof)│
             └────────────────────────┬─────────────────────────┘
                                      │
                                      ▼
             ┌──────────────────────────────────────────────────┐
             │ 4. SECOND BRAIN RECOVERY & DOCKER DEPLOYMENT     │
             │   (Redis WAL Checkpoints + Automated Rule Base)  │
             └──────────────────────────────────────────────────┘
```

---

## 🤖 Supported Models & Providers

| Provider Gateway | Base URL | Selected Model IDs | Specialized Role |
| :--- | :--- | :--- | :--- |
| **OpenRouter** | `https://openrouter.ai/api/v1` | `baidu/ernie-5.5-flash-preview:free`<br>`cohere/north-mini-code:free`<br>`nvidia/nemotron-3.5-lightning:free` | 1.0M context frontier reasoning, sub-second code generation, fast agent loops. |
| **Free.ai Grant Mesh** | `https://api.free.ai/v1` | `qwen-coder`<br>`qwen7b`<br>`deepseek-r1-7b` | 15M token startup grant: full-stack coding, general execution, chain-of-thought thinking. |
| **Langfuse Observability** | `https://hipaa.cloud.langfuse.com` | N/A | Production AI tracing, generation spans, latency & token telemetry under HIPAA-ready cloud. |
| **Respan Gateway** | `https://gateway.respan.ai/v1` | `respan/gemini-4-carbon:free`<br>`meta/muse-ember:free` | Frontier logic proofs, formal verification, multimodal UI wireframing. |
| **Experiential Labs** | `https://api.experientiallabs.ai/v1` | `claude-fable-5.2:free`<br>`gpt-6-luna`<br>`clef` | Long-horizon cognitive peer review, zero-data-retention decisions. |
| **APInex Gateway** | `https://api.apinex.bond/v1` | `free/jev-1.13`<br>`free/qwen-3.8-max`<br>`free/deepseek-v4-pro-0813`<br>`free/kimi-k3` | Decision routing, dense backend coding, security auditing, real-time web search tool. |
| **Coarena (Emergency Gate)**| `https://coarena.ai/api/v1` | `gpt-6-1-sol` | Reserved strictly for tie-breaking deadlocks under budget caps. |

---

## 🚀 Quick Start

### 1. Clone & Setup Environment
```bash
git clone https://github.com/Akshu1245/harness.git
cd harness
cp .env.example .env
```

Add your API keys to `.env`:
```env
OPENROUTER_API_KEY=your_openrouter_key
FREE_AI_API_KEY=your_free_ai_key
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
LANGFUSE_SECRET_KEY=your_langfuse_secret_key
LANGFUSE_BASE_URL=https://hipaa.cloud.langfuse.com
RESPAN_API_KEY=your_respan_key
EXPLABS_API_KEY=your_explabs_key
APINEX_API_KEY=your_apinex_key
COARENA_API_KEY=your_coarena_key
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Live Multi-Gateway Health Check
```bash
python verify_all_gateways.py
```

### 4. Launch Autonomous Loop Cycle
```bash
python autonomous_loop_engine.py
```

### 5. Launch the Visual War Room
Open [`visual_war_room.html`](./visual_war_room.html) in your browser:
```bash
# Windows
start visual_war_room.html
# macOS
open visual_war_room.html
```

---

## 🔒 Security & Privacy Notice
All `.env` files and active credentials are strictly excluded via `.gitignore`. Never commit live API tokens to version control.

---

## 📄 License
MIT License. Open for development, expansion, and autonomous research.
