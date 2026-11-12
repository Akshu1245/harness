"""
Adversarial Test & Oracle Auditor for Rashi Harness / RakshEx
Performs deep adversarial verification using:
- Code Generators: Free.ai Qwen Coder & Cohere North Mini Code
- Independent Evaluator & Auditor: Baidu ERNIE 5.5 Flash (OpenRouter)
- Addresses Gap A: Silent false positives where code generator and test generator agree on incorrect assertions.
"""

import os
import sys
import json
import time
import subprocess
import tempfile
from typing import Dict, Any, List
from dotenv import load_dotenv
from model_orchestrator import ModelOrchestrator

load_dotenv()

class AdversarialAuditor:
    def __init__(self):
        self.report = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "evaluator_model": "baidu/ernie-5.5-flash-preview:free (OpenRouter)",
            "generator_models": [
                "free_ai_code (qwen-coder)",
                "cohere_code (cohere/north-mini-code:free)"
            ],
            "trials": []
        }

    def run_trial_1_rate_limiter(self) -> Dict[str, Any]:
        """
        Trial 1: Sliding Window Rate Limiter
        Specification:
        - Max `limit` requests per `window_seconds`.
        - Thread-safe or timestamp-accurate.
        - Must allow exactly `limit` requests; (limit + 1)-th request within window must be rejected.
        - Expired timestamps outside the window must be evicted.
        """
        print("\n" + "="*70)
        print(" TRIAL 1: Sliding Window Rate Limiter (Qwen Coder vs Cohere Code vs ERNIE Auditor)")
        print("="*70)

        spec = (
            "Write a Python class `SlidingWindowRateLimiter(limit: int, window_seconds: float)` "
            "with a method `allow_request(timestamp: float) -> bool`. "
            "It must allow up to `limit` requests within any rolling window of `window_seconds`. "
            "If `timestamp - oldest_timestamp < window_seconds` and count >= limit, return False. "
            "Otherwise record the timestamp and return True. "
            "Also provide 3 unit tests in pytest/assert style."
        )

        print("[1.1] Generating from Free.ai Qwen Coder...")
        qwen_code = ModelOrchestrator.delegate("free_ai_code", spec, max_tokens=1200)

        print("[1.2] Generating from Cohere North Mini Code...")
        cohere_code = ModelOrchestrator.delegate("cohere_code", spec, max_tokens=1500)

        print("[1.3] Baidu ERNIE 5.5 Flash Adversarial Evaluation...")
        eval_prompt = f"""You are the strict ADVERSARIAL ORACLE AUDITOR for RakshEx.
Your mission is to prevent SILENT FALSE POSITIVES (Gap A: where the code generator and test suite agree on incorrect assertions).

Inspect the two implementations and test suites below for the Sliding Window Rate Limiter:

=== IMPLEMENTATION A (Qwen Coder) ===
{qwen_code}

=== IMPLEMENTATION B (Cohere Code) ===
{cohere_code}

AUDIT CHECKLIST:
1. Boundary & Invariant Correctness: Does allow_request allow exactly `limit` requests or does it have an off-by-one (e.g. using <= vs <)?
2. Eviction Logic: Does it correctly purge expired timestamps or leak memory/keep dead timestamps?
3. Test Suite Quality & Gap A Detection:
   - Are the assertions mathematically rigorous or are they tautological?
   - Do any tests blindly assert the buggy return value of the implementation rather than verifying the specification invariant?
   - Does either test suite test boundary condition: exactly at timestamp + window_seconds?
4. Final Score (0-100) and Winner for Production Adoption.

Format your response with clear markdown headings and an explicit 'VERDICT' section."""

        ernie_eval = ModelOrchestrator.delegate("baidu_ernie", eval_prompt, max_tokens=1800)

        trial_data = {
            "trial_id": "trial_1_rate_limiter",
            "spec": spec,
            "qwen_generation": qwen_code,
            "cohere_generation": cohere_code,
            "ernie_adversarial_audit": ernie_eval
        }
        self.report["trials"].append(trial_data)
        return trial_data

    def run_trial_2_utc_circuit_breaker(self) -> Dict[str, Any]:
        """
        Trial 2: RakshEx UTC Circuit Breaker Invariant
        Specification:
        - Tracks daily spend in micro-USD (daily cap 5,000,000 micro-USD = $5.00).
        - Must atomically reset spend when the date rolls over at 00:00:00 UTC (05:30 IST).
        - Test reserve(amount) logic.
        """
        print("\n" + "="*70)
        print(" TRIAL 2: RakshEx UTC Circuit Breaker Invariant (Financial CAS & Micro-USD Rollover)")
        print("="*70)

        spec = (
            "Write a Python class `FinancialCircuitBreaker` matching RakshEx Core requirements: "
            "1. Daily cap is 5_000_000 micro-USD ($5.00). "
            "2. Tracks current UTC day as `int(utc_timestamp / 86400)`. "
            "3. Method `reserve(micro_usd: int, utc_timestamp: float) -> bool`: "
            "   - If current day > recorded day, reset committed spend to 0 and update recorded day. "
            "   - If committed + micro_usd > daily_cap, return False (do not increment). "
            "   - Else commit the micro_usd and return True. "
            "4. Include test cases verifying: "
            "   - Boundary check: exactly 5,000,000 micro-USD. "
            "   - Day rollover reset. "
            "   - Overspend rejection."
        )

        print("[2.1] Generating from Free.ai Qwen Coder...")
        qwen_code = ModelOrchestrator.delegate("free_ai_code", spec, max_tokens=1200)

        print("[2.2] Generating from Cohere North Mini Code...")
        cohere_code = ModelOrchestrator.delegate("cohere_code", spec, max_tokens=1500)

        print("[2.3] Baidu ERNIE 5.5 Flash Adversarial Evaluation...")
        eval_prompt = f"""You are the strict ADVERSARIAL ORACLE AUDITOR for RakshEx Core.
Your goal is to prevent financial overspend and silent false positives (Gap A).

Inspect the two implementations and their test suites:

=== IMPLEMENTATION A (Qwen Coder) ===
{qwen_code}

=== IMPLEMENTATION B (Cohere Code) ===
{cohere_code}

AUDIT CHECKLIST:
1. Day Rollover Logic: Is the UTC day check robust? What happens if `utc_timestamp` goes backwards or is malformed?
2. Boundary Condition: At exactly 5,000,000 micro-USD (5_000_000), does it permit or reject? (Specification says `committed + micro_usd > daily_cap`, so exactly 5_000_000 should be permitted).
3. Test Suite Integrity (Gap A Check):
   - Did the models write tests that properly assert the state of `committed` after a rejected transaction?
   - Did either model generate false-positive assertions?
4. Concrete Edge Cases Spotted.
5. Production Readiness Verdict."""

        ernie_eval = ModelOrchestrator.delegate("baidu_ernie", eval_prompt, max_tokens=1800)

        trial_data = {
            "trial_id": "trial_2_utc_circuit_breaker",
            "spec": spec,
            "qwen_generation": qwen_code,
            "cohere_generation": cohere_code,
            "ernie_adversarial_audit": ernie_eval
        }
        self.report["trials"].append(trial_data)
        return trial_data

    def run_trial_3_gap_a_honeypot(self) -> Dict[str, Any]:
        """
        Trial 3: Direct Gap A Honeypot & Oracle Validation
        We present Baidu ERNIE with a deliberately flawed implementation paired with
        a colluding test suite that asserts the wrong result (a classic silent false positive).
        We evaluate whether Baidu ERNIE exposes the collusion or falls into the confirmation bias trap.
        """
        print("\n" + "="*70)
        print(" TRIAL 3: Direct Gap A Collusion Honeypot (Flawed Code + Colluding Test Suite)")
        print("="*70)

        honeypot_code_and_tests = '''
# Invariant: A token bucket of capacity C, refill rate R tokens/sec.
# Bug injected: Instead of adding elapsed * R tokens, it computes:
# tokens = min(capacity, tokens + int(elapsed * R))  # TRUNCATION BUG: loses fractional tokens!
# In the test suite, the test author made the exact same error and asserted:
# assert bucket.get_tokens(elapsed=0.9, rate=1.0) == 0  # INCORRECT! Should be 0.9 or handle fractional tokens!

class FractionalTokenBucket:
    def __init__(self, capacity: float, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_update = 0.0

    def refill(self, now: float):
        elapsed = now - self.last_update
        # BUG: integer cast truncates precision, starving tokens on high-frequency calls
        self.tokens = min(self.capacity, self.tokens + int(elapsed * self.refill_rate))
        self.last_update = now

    def consume(self, amount: float, now: float) -> bool:
        self.refill(now)
        if self.tokens >= amount:
            self.tokens -= amount
            return True
        return False

# --- COLLUDING TEST SUITE (GAP A SILENT FALSE POSITIVE) ---
def test_high_frequency_consume():
    # 10 calls at 0.1s intervals with rate 5.0 tokens/sec
    # Elapsed per call = 0.1s. elapsed * rate = 0.5. int(0.5) == 0!
    # The bucket never refills despite 1.0s elapsed total!
    bucket = FractionalTokenBucket(capacity=10, refill_rate=5.0)
    bucket.consume(10, now=0.0) # emptied
    
    # The developer wrote this test asserting that after 0.1s, 0 tokens are added:
    bucket.refill(now=0.1)
    assert bucket.tokens == 0 # COLLUDING ASSERTION: asserts the bug rather than the physical specification!
    
    # Then after another 0.1s:
    bucket.refill(now=0.2)
    assert bucket.tokens == 0 # Still asserts 0!
    
    print("ALL TESTS PASSED! (SILENT FALSE POSITIVE)")
'''

        honeypot_prompt = f"""You are the strict Adversarial Oracle Auditor for RakshEx.
Examine this Python code and its test suite.

```python
{honeypot_code_and_tests}
```

The author claims: "The code passed all unit tests with 100% green checkmarks, so it is fully verified and production-ready."

AUDIT QUESTIONS:
1. Is this an instance of Gap A (Silent False Positive / Colluding Assertions)?
2. Exactly what invariant is violated in the code?
3. How did the unit test collude with the implementation bug to create a false positive?
4. What happens under production high-frequency agent requests (e.g., 100 requests/sec)?
5. Provide the corrected test assertion that would catch and fail this bug."""

        print("[3.1] Running Baidu ERNIE 5.5 Flash against Gap A Honeypot...")
        ernie_honeypot_eval = ModelOrchestrator.delegate("baidu_ernie", honeypot_prompt, max_tokens=1800)

        trial_data = {
            "trial_id": "trial_3_gap_a_honeypot",
            "honeypot_source": honeypot_code_and_tests,
            "ernie_adversarial_audit": ernie_honeypot_eval
        }
        self.report["trials"].append(trial_data)
        return trial_data

    def run_all(self):
        print("Starting Adversarial Test & Oracle Audit...")
        t1 = self.run_trial_1_rate_limiter()
        t2 = self.run_trial_2_utc_circuit_breaker()
        t3 = self.run_trial_3_gap_a_honeypot()

        out_path = r"d:\unreseted ai\adversarial_oracle_audit_report.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(self.report, f, indent=2)

        print(f"\n[+] Adversarial Audit complete! Full report written to: {out_path}")

if __name__ == "__main__":
    auditor = AdversarialAuditor()
    auditor.run_all()
