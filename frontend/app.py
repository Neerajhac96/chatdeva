"""
frontend/app.py — ChatDEVA Student Chat UI
-------------------------------------------
Fixed in this version:
  - Log Out button correctly inside sidebar
  - Admin Panel link correctly inside sidebar
  - Usage meter correctly inside sidebar
  - Clean indentation throughout
"""

import json
import datetime
import streamlit as st
import requests
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from config import settings

API = settings.BACKEND_URL
st.set_page_config(page_title="ChatDEVA", layout="wide", page_icon="🎓")


# ── API helpers ───────────────────────────────────────────────────────
def api_get(path, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        return requests.get(f"{API}{path}", headers=headers, timeout=15)
    except Exception as e:
        st.error(f"Cannot reach backend: {e}")
        return None


def api_post(path, data=None, json_data=None, token=None, files=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        return requests.post(f"{API}{path}", data=data, json=json_data,
                             headers=headers, files=files, timeout=30)
    except Exception as e:
        st.error(f"Cannot reach backend: {e}")
        return None


def api_delete(path, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        return requests.delete(f"{API}{path}", headers=headers, timeout=15)
    except Exception as e:
        st.error(f"Cannot reach backend: {e}")
        return None


# ── Session state defaults ────────────────────────────────────────────
for key, default in [
    ("token", None),
    ("user", None),
    ("current_session_id", None),
    ("messages", []),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ── Greeting ──────────────────────────────────────────────────────────
def get_greeting():
    h = datetime.datetime.now().hour
    if h < 12:   return "🌞 Good morning!"
    elif h < 17: return "🌤 Good afternoon!"
    elif h < 21: return "🌙 Good evening!"
    else:        return "🌙 Good night!"


# ── Auth page ─────────────────────────────────────────────────────────
def render_auth():
    st.title("👋 Welcome to ChatDEVA")
    st.markdown("Your college AI assistant — ask anything about your college.")
    st.divider()

    try:
        resp = api_get("/auth/colleges")
        colleges = resp.json() if resp and resp.status_code == 200 else []
        college_map = {c["name"]: c["id"] for c in colleges}
    except Exception:
        st.error("❌ Cannot reach backend. Make sure FastAPI is running.")
        return

    if not college_map:
        st.warning("No colleges registered yet. Contact your administrator.")
        return

    login_tab, register_tab = st.tabs(["🔑 Log In", "📝 Register"])

    with login_tab:
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Log In", use_container_width=True):
            if not username or not password:
                st.warning("Please fill in both fields.")
            else:
                resp = api_post("/auth/login", json_data={
                    "username": username,
                    "password": password,
                })
                if resp and resp.status_code == 200:
                    token     = resp.json()["access_token"]
                    user_resp = api_get("/auth/me", token=token)
                    if user_resp and user_resp.status_code == 200:
                        st.session_state.token = token
                        st.session_state.user  = user_resp.json()
                        st.rerun()
                else:
                    st.error("❌ Incorrect username or password.")

    with register_tab:
        st.markdown("Create a new **student** account.")
        college_name = st.selectbox("Your College", list(college_map.keys()), key="reg_college")
        reg_user     = st.text_input("Choose a username", key="reg_user")
        reg_pass     = st.text_input("Password (min 6 chars)", type="password", key="reg_pass")
        reg_confirm  = st.text_input("Confirm password", type="password", key="reg_confirm")

        if st.button("Create Account", use_container_width=True):
            if not reg_user.strip():
                st.warning("Username cannot be empty.")
            elif reg_pass != reg_confirm:
                st.error("❌ Passwords do not match.")
            elif len(reg_pass) < 6:
                st.warning("Password must be at least 6 characters.")
            else:
                resp = api_post("/auth/register", json_data={
                    "username":   reg_user.strip(),
                    "password":   reg_pass,
                    "college_id": college_map[college_name],
                    "role":       "student",
                })
                if resp and resp.status_code == 201:
                    st.success("✅ Account created! Switch to the Log In tab.")
                else:
                    detail = resp.json().get("detail", "Registration failed.") if resp else "Error"
                    st.error(f"❌ {detail}")


# ── Main app ──────────────────────────────────────────────────────────
def render_app():
    user  = st.session_state.user
    token = st.session_state.token

    # ── Sidebar ───────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(f"### 👤 {user['username']}")
        st.caption(f"{user['role'].capitalize()} · {get_greeting()}")
        st.divider()

        # ── Chat sessions ─────────────────────────────────────────────
        st.markdown("**💬 Chat Sessions**")

        if st.button("➕ New Chat", use_container_width=True):
            resp = api_post("/chat/sessions", json_data={"title": "New Chat"}, token=token)
            if resp and resp.status_code == 201:
                session = resp.json()
                st.session_state.current_session_id = session["id"]
                st.session_state.messages = []
                st.rerun()

        # List sessions
        sessions_resp = api_get("/chat/sessions", token=token)
        sessions = sessions_resp.json() if sessions_resp and sessions_resp.status_code == 200 else []

        for s in sessions:
            col1, col2 = st.columns([4, 1])
            with col1:
                label = s["title"][:30] + "..." if len(s["title"]) > 30 else s["title"]
                is_active = st.session_state.current_session_id == s["id"]
                btn_label = f"▶ {label}" if is_active else label
                if st.button(btn_label, key=f"sess_{s['id']}", use_container_width=True):
                    st.session_state.current_session_id = s["id"]
                    msgs_resp = api_get(f"/chat/sessions/{s['id']}/messages", token=token)
                    if msgs_resp and msgs_resp.status_code == 200:
                        st.session_state.messages = [
                            {
                                "role":    m["role"],
                                "content": m["content"],
                                "sources": json.loads(m.get("sources", "[]")),
                            }
                            for m in msgs_resp.json()
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
            if st.button("🗑️ Clear All Chats", use_container_width=True):
                api_delete("/chat/sessions", token=token)
                st.session_state.current_session_id = None
                st.session_state.messages = []
                st.rerun()

        st.divider()

        # ── Usage meter (students only) ───────────────────────────────
        if user["role"] == "student":
            usage_resp = api_get("/auth/usage", token=token)
            if usage_resp and usage_resp.status_code == 200:
                usage     = usage_resp.json()
                used      = usage.get("used", 0)
                limit     = usage.get("monthly_limit", 100)
                remaining = usage.get("remaining", 100)
                st.markdown("**📊 Monthly Usage**")
                st.progress(min(used / limit, 1.0) if limit > 0 else 0)
                st.caption(f"{used}/{limit} questions · {remaining} remaining")
                if remaining == 0:
                    st.warning("⚠️ Monthly limit reached. Contact your admin.")
                st.divider()

        # ── Admin panel link (admin/staff only) ───────────────────────
        if user["role"] in ("admin", "staff"):
            st.page_link("pages/admin.py", label="🛠️ Admin Panel")
            st.divider()

        # ── Log out ───────────────────────────────────────────────────
        if st.button("🚪 Log Out", use_container_width=True):
            for k in ["token", "user", "current_session_id", "messages"]:
                st.session_state[k] = None if k != "messages" else []
            st.rerun()

    # ── Main content area ─────────────────────────────────────────────
    st.title("ChatDEVA 🎓")
    st.caption(f"Logged in as **{user['username']}** · {user['role'].capitalize()}")

    if not st.session_state.current_session_id:
        st.info("👈 Click **➕ New Chat** in the sidebar to get started.")
        return

    # ── Display messages ──────────────────────────────────────────────
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            sources = msg.get("sources", [])
            if sources:
                st.markdown("---")
                st.markdown("**Sources:**")
                for src in sources:
                    st.caption(
                        f"📘 {src.get('filename', '')} · "
                        f"{src.get('doc_type', '')} · "
                        f"uploaded {src.get('uploaded_at', '')}"
                    )

    # ── Chat input ────────────────────────────────────────────────────
    if query := st.chat_input("Ask a question about your college documents..."):
        st.chat_message("user").markdown(query)
        st.session_state.messages.append({"role": "user", "content": query, "sources": []})

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                resp = api_post("/chat/ask", json_data={
                    "session_id": st.session_state.current_session_id,
                    "query":      query,
                }, token=token)

            if resp and resp.status_code == 200:
                data    = resp.json()
                answer  = data["answer"]
                sources = data["sources"]
            elif resp and resp.status_code == 429:
                answer  = "⚠️ " + resp.json().get("detail", "Monthly limit reached.")
                sources = []
            else:
                detail  = resp.json().get("detail", "Unknown error") if resp else "Connection error"
                answer  = f"⚠️ Error: {detail}"
                sources = []

            st.markdown(answer)
            if sources:
                st.markdown("---")
                st.markdown("**Sources:**")
                for src in sources:
                    st.caption(
                        f"📘 {src['filename']} · "
                        f"{src['doc_type']} · "
                        f"uploaded {src['uploaded_at']}"
                    )

        st.session_state.messages.append({
            "role":    "assistant",
            "content": answer,
            "sources": sources,
        })


# ── Entry point ───────────────────────────────────────────────────────
if st.session_state.token is None:
    render_auth()
else:
    render_app()
