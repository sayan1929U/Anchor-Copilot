"""
Runs the labeled eval set against the live orchestrator and reports:
- Intent classification accuracy
- Source grounding accuracy (did it cite the expected doc?)
- Guardrail block rate (how often the hallucination checker fired)

Run: python -m tests.eval.run_eval
Exits with code 1 if intent accuracy or grounding rate falls below threshold -
this is what lets CI actually fail the build on a real regression.
"""
import json
import sys
import time
from app.database import SessionLocal
from app.models.conversation import ConversationSession
from app.agents.orchestrator import route

INTENT_ACCURACY_THRESHOLD = 85.0
GROUNDING_RATE_THRESHOLD = 85.0

with open("tests/eval/test_cases.json") as f:
    test_cases = json.load(f)["test_cases"]


def run_eval():
    db = SessionLocal()
    results = []

    for i, case in enumerate(test_cases, 1):
        message = case["message"]
        expected_intent = case["expected_intent"]
        expected_source = case["expected_source"]

        session = ConversationSession(employee_id=1)
        db.add(session)
        db.commit()
        db.refresh(session)

        start = time.time()
        result = route(message, db, session.id, employee_id=1)
        elapsed = round(time.time() - start, 2)

        intent_correct = result.intent == expected_intent
        source_correct = expected_source in (result.sources or [])
        was_blocked = "accurate information rather than guess" in result.content

        results.append({
            "message": message,
            "expected_intent": expected_intent,
            "actual_intent": result.intent,
            "intent_correct": intent_correct,
            "expected_source": expected_source,
            "actual_sources": result.sources,
            "source_correct": source_correct,
            "blocked_by_guardrail": was_blocked,
            "latency_sec": elapsed,
        })

        status = "PASS" if intent_correct and source_correct and not was_blocked else "FAIL"
        print(f"[{i}/{len(test_cases)}] {status} - {message[:50]}")

    db.close()
    return results


def summarize(results):
    total = len(results)
    intent_acc = sum(r["intent_correct"] for r in results) / total * 100
    source_acc = sum(r["source_correct"] for r in results) / total * 100
    block_rate = sum(r["blocked_by_guardrail"] for r in results) / total * 100
    avg_latency = sum(r["latency_sec"] for r in results) / total

    print("\n" + "=" * 50)
    print("EVAL SUMMARY")
    print("=" * 50)
    print(f"Total test cases:        {total}")
    print(f"Intent accuracy:         {intent_acc:.1f}%")
    print(f"Source grounding rate:   {source_acc:.1f}%")
    print(f"Guardrail block rate:    {block_rate:.1f}%")
    print(f"Avg latency per request: {avg_latency:.2f}s")

    failures = [r for r in results if not (r["intent_correct"] and r["source_correct"] and not r["blocked_by_guardrail"])]
    if failures:
        print(f"\n{len(failures)} FAILURES:")
        for f in failures:
            print(f"  - \"{f['message'][:60]}\"")
            print(f"    expected intent={f['expected_intent']} got={f['actual_intent']}, "
                  f"expected_source={f['expected_source']} got={f['actual_sources']}, "
                  f"blocked={f['blocked_by_guardrail']}")

    return intent_acc, source_acc


if __name__ == "__main__":
    results = run_eval()
    intent_acc, source_acc = summarize(results)

    with open("tests/eval/last_run_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    if intent_acc < INTENT_ACCURACY_THRESHOLD or source_acc < GROUNDING_RATE_THRESHOLD:
        print(f"\nFAILING BUILD: accuracy below threshold "
              f"(intent {intent_acc:.1f}% / grounding {source_acc:.1f}%, need >= {INTENT_ACCURACY_THRESHOLD}%)")
        sys.exit(1)

    print("\nEval suite passed threshold.")
    sys.exit(0)
