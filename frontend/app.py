"""
frontend/app.py — Student chat UI
-----------------------------------
All logic goes through the FastAPI backend via HTTP.
JWT token stored in st.session_state after login.
Students can: login, register, chat, manage their own sessions.
Admins/staff see an extra "Admin Panel" link in the sidebar.

Run: streamlit run frontend/app.py
"""

import json
import datetime
import streamlit as st
import requests

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from config import settings

API = settings.BACKEND_URL
st.set_page_config(page_title="ChatDEVA", layout="wide")


# ── API helpers ───────────────────────────────────────────────────────
def api_get(path, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return requests.get(f"{API}{path}", headers=headers)


def api_post(path, data=None, json_data=None, token=None, files=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return requests.post(f"{API}{path}", data=data, json=json_data,
                         headers=headers, files=files)


def api_delete(path, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return requests.delete(f"{API}{path}", headers=headers)


# ── Session state defaults ────────────────────────────────────────────
for key, default in [
    ("token", None), ("user", None), ("current_session_id", None),
    ("messages", []),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ── Auth gate ─────────────────────────────────────────────────────────
def render_auth():
    st.title("👋 Welcome to ChatDEVA")
    st.markdown("Your college AI assistant.")

    # Fetch colleges for dropdown
    try:
        colleges = api_get("/auth/colleges").json()
        college_map = {c["name"]: c["id"] for c in colleges}
    except Exception:
        st.error("Cannot reach backend. Make sure FastAPI is running.")
        return

    login_tab, register_tab = st.tabs(["🔑 Log In", "📝 Register"])

    with login_tab:
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Log In"):
            if not username or not password:
                st.warning("Please fill in both fields.")
                return
            resp = api_post("/auth/login", json_data={
                "username": username, "password": password
            })
            if resp.status_code == 200:
                token = resp.json()["access_token"]
                user_resp = api_get("/auth/me", token=token)
                st.session_state.token = token
                st.session_state.user  = user_resp.json()
                st.rerun()
            else:
                st.error("❌ Incorrect username or password.")

    with register_tab:
        st.markdown("Create a new **student** account.")
        college_name = st.selectbox("College", list(college_map.keys()), key="reg_college")
        reg_user     = st.text_input("Username", key="reg_user")
        reg_pass     = st.text_input("Password (min 6 chars)", type="password", key="reg_pass")
        reg_confirm  = st.text_input("Confirm password", type="password", key="reg_confirm")

        if st.button("Create Account"):
            if reg_pass != reg_confirm:
                st.error("Passwords do not match.")
            elif len(reg_pass) < 6:
                st.warning("Password must be at least 6 characters.")
            else:
                resp = api_post("/auth/register", json_data={
                    "username":   reg_user,
                    "password":   reg_pass,
                    "college_id": college_map[college_name],
                    "role":       "student",
                })
                if resp.status_code == 201:
                    st.success("✅ Account created! Switch to Log In.")
                else:
                    st.error(resp.json().get("detail", "Registration failed."))


# ── Main app ──────────────────────────────────────────────────────────
def render_app():
    user  = st.session_state.user
    token = st.session_state.token

    st.title("ChatDEVA 🎓")

    def get_greeting():
        h = datetime.datetime.now().hour
        if h < 12:   return "🌞 Good morning!"
        elif h < 17: return "🌤 Good afternoon!"
        elif h < 21: return "🌙 Good evening!"
        else:        return "🌙 Good night!"

    st.markdown(get_greeting())
    st.caption(f"Logged in as **{user['username']}** · {user['role'].capitalize()}")

    # ── Sidebar ───────────────────────────────────────────────────────
    with st.sidebar:
        st.header("💬 Chat Sessions")

        if st.button("➕ New Chat"):
            resp = api_post("/chat/sessions", json_data={"title": "New Chat"}, token=token)
            if resp.status_code == 201:
                session = resp.json()
                st.session_state.current_session_id = session["id"]
                st.session_state.messages = []
                st.rerun()

        # List sessions
        sessions_resp = api_get("/chat/sessions", token=token)
        sessions = sessions_resp.json() if sessions_resp.status_code == 200 else []

        for s in sessions:
            col1, col2 = st.columns([4, 1])
            with col1:
                label = s["title"][:35] + "..." if len(s["title"]) > 35 else s["title"]
                if st.button(label, key=f"sess_{s['id']}"):
                    st.session_state.current_session_id = s["id"]
                    # Load messages for this session
                    msgs_resp = api_get(f"/chat/sessions/{s['id']}/messages", token=token)
                    if msgs_resp.status_code == 200:
                        raw = msgs_resp.json()
                        st.session_state.messages = [
                            {
                                "role": m["role"],
                                "content": m["content"],
                                "sources": json.loads(m.get("sources", "[]")),
                            }
                            for m in raw
                        ]
                    st.rerun()
            with col2:
                if st.button("🗑️", key=f"del_sess_{s['id']}"):
                    api_delete(f"/chat/sessions/{s['id']}", token=token)
                    if st.session_state.current_session_id == s["id"]:
                        st.session_state.current_session_id = None
                        st.session_state.messages = []
                    st.rerun()

        if sessions:
            if st.button("🗑️ Clear All Chats"):
                api_delete("/chat/sessions", token=token)
                st.session_state.current_session_id = None
                st.session_state.messages = []
                st.rerun()

        st.divider()

        # Admin panel link for admin/staff
        if user["role"] in ("admin", "staff"):
            st.page_link("pages/admin.py", label="🛠️ Admin Panel", icon="🛠️")

        if st.button("🚪 Log Out"):
            for k in ["token", "user", "current_session_id", "messages"]:
                st.session_state[k] = None if k != "messages" else []
            st.rerun()

    # ── Chat area ─────────────────────────────────────────────────────
    if not st.session_state.current_session_id:
        st.info("👈 Click **➕ New Chat** in the sidebar to get started.")
        return

    # Display messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            sources = msg.get("sources", [])
            if sources:
                st.markdown("---")
                st.markdown("**Sources:**")
                for src in sources:
                    fname    = src.get("filename", "")
                    doc_type = src.get("doc_type", "")
                    uploaded = src.get("uploaded_at", "")
                    st.caption(f"📘 {fname} · {doc_type} · uploaded {uploaded}")

    # Chat input
    if query := st.chat_input("Ask a question about your college documents..."):
        # Show user message immediately
        st.chat_message("user").markdown(query)
        st.session_state.messages.append({"role": "user", "content": query, "sources": []})

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                resp = api_post("/chat/ask", json_data={
                    "session_id": st.session_state.current_session_id,
                    "query": query,
                }, token=token)

            if resp.status_code == 200:
                data    = resp.json()
                answer  = data["answer"]
                sources = data["sources"]   # list of SourceMeta dicts
            else:
                answer  = f"⚠️ Error: {resp.json().get('detail', 'Unknown error')}"
                sources = []

            st.markdown(answer)
            if sources:
                st.markdown("---")
                st.markdown("**Sources:**")
                for src in sources:
                    st.caption(f"📘 {src['filename']} · {src['doc_type']} · uploaded {src['uploaded_at']}")

        st.session_state.messages.append({
            "role": "assistant", "content": answer, "sources": sources
        })


# ── Entry point ───────────────────────────────────────────────────────
if st.session_state.token is None:
    render_auth()
else:
    render_app()
