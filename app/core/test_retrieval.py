from app.core.retrieval import retrieve_chunks

test_queries = [
    "What happens if I am struggling financially?",
    "How do promotions work here?",
    "I want to learn new skills, what's available?",
]

for q in test_queries:
    print(f"\nQuery: {q}")
    results = retrieve_chunks(q, top_k=2)
    for r in results:
        print(f"  [{r.category}] {r.content[:80]}...")
