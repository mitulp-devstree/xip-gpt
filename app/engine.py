import json
from app.agent import build_agent

agent = build_agent()


def ask_agent(query: str, thread_id: str = "default"):

    res = agent.invoke(
        {"messages": [("user", query)]},
        config={"configurable": {"thread_id": thread_id}}
    )

    explanation = res["messages"][-1].content
    
    candidates = []
    for msg in res["messages"]:
        if getattr(msg, "type", "") == "tool" and getattr(msg, "name", "") == "search_candidates":
            try:
                data = json.loads(msg.content)
                candidates.extend(data)
            except Exception:
                pass

    return {
        "explanation": explanation,
        "candidates": candidates
    }