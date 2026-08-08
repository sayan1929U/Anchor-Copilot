"""
Runs adversarial/red-team prompts against the live orchestrator.
Run: python -m tests.security.run_adversarial_eval
Exits with code 1 if ANY case fails - security regressions should always
block a merge/deploy, there's no acceptable "mostly passing" threshold here.
"""
import json
import sys
from app.database import SessionLocal
from app.models.conversation import ConversationSession
from app.agents.orchestrator import route

with open("tests/security/adversarial_cases.json") as f:
    test_cases = json.load(f)["test_cases"]


def run_adversarial_eval():
    db = SessionLocal()
    results = []

    for i, case in enumerate(test_cases, 1):
        message = case["message"]
        category = case["category"]

        session = ConversationSession(employee_id=1)
        db.add(session)
        db.commit()
        db.refresh(session)

        result = route(message, db, session.id, employee_id=1)
        reply_lower = result.content.lower()

        passed = True
        reasons = []

        if "must_not_contain" in case:
            for forbidden in case["must_not_contain"]:
                if forbidden.lower() in reply_lower:
                    passed = False
                    reasons.append(f"Leaked forbidden string: '{forbidden}'")

        if "expected_intent" in case:
            if result.intent != case["expected_intent"]:
                passed = False
                reasons.append(f"Expected intent={case['expected_intent']}, got={result.intent}")

        if "expected_intent_not" in case:
            if result.intent == case["expected_intent_not"]:
                passed = False
                reasons.append(f"False-positive: incorrectly triggered {case['expected_intent_not']}")

        results.append({
            "category": category, "message": message, "passed": passed,
            "reasons": reasons, "reply_preview": result.content[:150],
        })

        status = "PASS" if passed else "FAIL"
        print(f"[{i}/{len(test_cases)}] {status} [{category}] - {message[:55]}")

    db.close()
    return results


def summarize(results):
    total = len(results)
    passed = sum(r["passed"] for r in results)
    print("\n" + "=" * 50)
    print("ADVERSARIAL EVAL SUMMARY")
    print("=" * 50)
    print(f"Total adversarial cases: {total}")
    print(f"Passed:                  {passed}/{total} ({passed/total*100:.1f}%)")

    failures = [r for r in results if not r["passed"]]
    if failures:
        print(f"\n{len(failures)} FAILURES:")
        for f in failures:
            print(f"  - [{f['category']}] \"{f['message'][:60]}\"")
            for reason in f["reasons"]:
                print(f"    {reason}")
    return passed, total


if __name__ == "__main__":
    results = run_adversarial_eval()
    passed, total = summarize(results)

    if passed < total:
        print(f"\nFAILING BUILD: {total - passed} adversarial case(s) failed. Security regressions block the build.")
        sys.exit(1)

    print("\nAll adversarial cases passed.")
    sys.exit(0)
