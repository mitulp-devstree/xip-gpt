from app.engine import agent
for chunk, metadata in agent.stream({"messages": [("user", "hey")]}, config={"configurable": {"thread_id": "test_123"}}, stream_mode="messages"):
    print(f"type: {type(chunk)}")
    print(f"dict: {chunk.__dict__ if hasattr(chunk, '__dict__') else chunk}")
