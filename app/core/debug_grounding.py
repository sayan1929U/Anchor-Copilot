from app.agents.specialists import stability_agent
from app.core.retrieval import retrieve_chunks
from app.core.hallucination_check import check_grounding, _extract_claims

message = "Am I the only one delaying big life decisions because of money?"

result = stability_agent(message)
print("=== AGENT RESPONSE ===")
print(result.content)
print("\nSources:", result.sources)

claims = _extract_claims(result.content)
print("\n=== EXTRACTED CLAIMS (numbers/named phrases) ===")
print(claims)

chunks = retrieve_chunks(message, category="stability", top_k=3)
context_text = "\n\n".join(c.content for c in chunks)
print("\n=== RE-RETRIEVED CONTEXT (used by guardrail) ===")
for c in chunks:
    print(f"[{c.source}] {c.content[:150]}...\n")

is_grounded = check_grounding(result.content, context_text)
print("=== VERDICT ===")
print("Grounded:", is_grounded)
