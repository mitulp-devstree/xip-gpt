import streamlit as st
import requests

API_BASE = "http://api:8000"

st.title("AI Resume Search")

# ── Sidebar: Ingestion trigger ────────────────────────────────────────────────
with st.sidebar:
    st.header("🔄 Data Ingestion")
    st.caption("Re-index all resumes from MongoDB into the Qdrant vector store.")

    if st.button("▶ Run Ingestion", use_container_width=True):
        with st.spinner("Running ingestion pipeline..."):
            try:
                r = requests.post(f"{API_BASE}/ingest", timeout=300)
                data = r.json()
                if r.status_code == 200 and data.get("status") == "success":
                    st.success(
                        f"✅ Ingestion complete!\n\n"
                        f"- **Total resumes:** {data['total']}\n"
                        f"- **Indexed:** {data['indexed']}\n"
                        f"- **Failed:** {data['failed']}"
                    )
                else:
                    st.error(f"❌ Ingestion failed:\n\n{data.get('detail', data)}")
            except Exception as e:
                st.error(f"❌ Request error: {e}")

import uuid

# Initialize session state for chat history and thread ID
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    # `messages` will store dicts: {"role": "user"|"assistant", "content": "text...", "candidates": [...]}
    st.session_state.messages = []

# ── Main: Chat Interface ────────────────────────────────────────────────────
st.divider()

# Display chat history on app rerun
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        
        # Render candidate cards if they were part of this message
        candidates = msg.get("candidates", [])
        if candidates:
            st.markdown("#### Found Candidates")
            for i, cand in enumerate(candidates, start=1):
                with st.container(border=True):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        name = cand.get("name") or "Unknown Candidate"
                        st.subheader(f"{i}. {name}")
                        exp = cand.get("total_experience", "N/A")
                        city = cand.get("city", "N/A")
                        st.write(f"💼 **Experience:** {exp} years  |  📍 **Location:** {city}")
                        
                        skills = cand.get("skills", [])
                        if isinstance(skills, list) and skills:
                            st.write(f"🛠️ **Skills:** {', '.join(skills)}")
                        elif isinstance(skills, str) and skills:
                            st.write(f"🛠️ **Skills:** {skills}")
                    with col2:
                        with st.popover("Raw Data"):
                            st.json(cand)


# Handle user chat input
if prompt := st.chat_input("Ask for candidates or chat with the AI..."):
    # Output user message to UI immediately
    with st.chat_message("user"):
        st.write(prompt)
    
    # Store user message in state
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Show an interactive spinner for the assistant's turn
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                r = requests.post(
                    f"{API_BASE}/search", 
                    json={"query": prompt, "thread_id": st.session_state.thread_id}
                )
                if r.status_code == 200:
                    data = r.json()
                    
                    answerRaw = data.get("answer", "")
                    if isinstance(answerRaw, dict) and "text" in answerRaw:
                        answerRaw = answerRaw["text"]
                    elif isinstance(answerRaw, list):
                        answerRaw = " ".join([str(a.get("text", a) if isinstance(a, dict) else a) for a in answerRaw])
                    else:
                        answerRaw = str(answerRaw)
                        
                    # Stream the introductory text
                    def stream_text():
                        for word in answerRaw.split(" "):
                            yield word + " "
                    st.write_stream(stream_text)
                    
                    candidates = data.get("candidates", [])
                    if candidates:
                        st.markdown("#### Found Candidates")
                        for i, cand in enumerate(candidates, start=1):
                            with st.container(border=True):
                                col1, col2 = st.columns([3, 1])
                                with col1:
                                    name = cand.get("name") or "Unknown Candidate"
                                    st.subheader(f"{i}. {name}")
                                    exp = cand.get("total_experience", "N/A")
                                    city = cand.get("city", "N/A")
                                    st.write(f"💼 **Experience:** {exp} years  |  📍 **Location:** {city}")
                                    
                                    skills = cand.get("skills", [])
                                    if isinstance(skills, list) and skills:
                                        st.write(f"🛠️ **Skills:** {', '.join(skills)}")
                                    elif isinstance(skills, str) and skills:
                                        st.write(f"🛠️ **Skills:** {skills}")
                                
                                with col2:
                                    with st.popover("Raw Data"):
                                        st.json(cand)
                    
                    # Save assistant response to state
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": answerRaw,
                        "candidates": candidates
                    })
                    
                else:
                    st.error(f"❌ Error during search: {r.text}")
            except Exception as e:
                st.error(f"❌ Server connection error: {e}")