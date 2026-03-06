import json
from app.agent import build_agent

agent = build_agent()


async def ask_agent_stream(query: str, thread_id: str = "default"):
    """
    Streams the agent's response and tool call results.
    Yields JSON-encoded strings separated by newlines.
    """
    async for event in agent.astream_events(
        {"messages": [("user", query)]},
        config={"configurable": {"thread_id": thread_id}},
        version="v2"
    ):
        kind = event["event"]
        
        # When the LLM streams a chunk of the response text
        if kind == "on_chat_model_stream":
            content = event["data"]["chunk"].content
            if content:
                if isinstance(content, str):
                    yield json.dumps({"type": "chunk", "content": content}) + "\n"
                elif isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            yield json.dumps({"type": "chunk", "content": item.get("text", "")}) + "\n"
                
        # When a tool finishes executing
        elif kind == "on_tool_end":
            if event["name"] == "submit_candidates":
                try:
                    output = event["data"].get("output")
                    output_str = output.content if hasattr(output, "content") else str(output)
                    candidates_data = json.loads(output_str)
                    # Yield candidates payload
                    yield json.dumps({"type": "candidates", "data": candidates_data}) + "\n"
                except Exception as e:
                    yield json.dumps({"type": "error", "content": f"Failed to parse candidates: {str(e)}"}) + "\n"