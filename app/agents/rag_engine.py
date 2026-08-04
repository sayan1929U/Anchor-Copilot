from app.agents.base import AgentResponse
from app.core.retrieval import retrieve_chunks
from app.core.groq_client import safe_groq_call, FALLBACK_MESSAGE


def _build_context_block(chunks) -> str:
    if not chunks:
        return "No specific policy documents were found for this question."
    blocks = []
    for i, chunk in enumerate(chunks, start=1):
        blocks.append(f"[Source {i}: {chunk.source}]\n{chunk.content}")
    return "\n\n".join(blocks)


def generate_grounded_response(
    system_prompt: str,
    message: str,
    agent_name: str,
    category: str,
    history: list[dict] | None = None,
) -> AgentResponse:
    chunks = retrieve_chunks(message, category=category, top_k=3)
    context_block = _build_context_block(chunks)

    full_system_prompt = f"""{system_prompt}

You have access to the following retrieved company policy and research excerpts. Use ONLY this
information for any factual claims. If the excerpts don't cover what the person asked, say so
honestly rather than guessing - do not invent policy details.

When you reference a specific fact from the excerpts, mention which source it came from.

You also have access to the recent conversation history below. Use it to maintain continuity -
don't re-introduce yourself if you've already spoken, and reference earlier context naturally
where relevant (e.g. "as you mentioned earlier...").

--- RETRIEVED CONTEXT ---
{context_block}
--- END CONTEXT ---
"""

    messages = [{"role": "system", "content": full_system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": message})

    response = safe_groq_call(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.4,
        max_tokens=300,
    )

    if response is None:
        return AgentResponse(agent_name=agent_name, content=FALLBACK_MESSAGE, sources=[])

    content = response.choices[0].message.content or "Let me look into that further with you."
    sources = list({chunk.source for chunk in chunks})

    return AgentResponse(agent_name=agent_name, content=content, sources=sources)
