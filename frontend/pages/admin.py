"""
frontend/pages/admin.py — Admin Panel
---------------------------------------
Streamlit multi-page app — auto-discovered by Streamlit from pages/ folder.
All data fetched from FastAPI backend via JWT-authenticated HTTP calls.
Accessible only to admin/staff roles — enforced both here (UI) and
at the API level (require_staff / require_admin dependencies).

Tabs:
  📄 Documents  — upload, view, delete, re-index
  👥 Users      — list, create admin/staff, change role, deactivate
  💬 Chat Monitor — view all sessions + messages in college
  📋 Audit Log  — recent security events
"""

import json
import sys
import os
import streamlit as st
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
from config import settings

API = settings.BACKEND_URL
st.set_page_config(page_title="ChatDEVA — Admin", layout="wide")


# ── API helpers ───────────────────────────────────────────────────────
def api_get(path, token):
    return requests.get(f"{API}{path}", headers={"Authorization": f"Bearer {token}"})


def api_post(path, token, json_data=None, data=None, files=None):
    return requests.post(
        f"{API}{path}",
        headers={"Authorization": f"Bearer {token}"},
        json=json_data, data=data, files=files,
    )


def api_delete(path, token):
    return requests.delete(f"{API}{path}", headers={"Authorization": f"Bearer {token}"})


def api_patch(path, token, json_data=None):
    return requests.patch(
        f"{API}{path}",
        headers={"Authorization": f"Bearer {token}"},
        json=json_data,
    )


# ── Access control ────────────────────────────────────────────────────
if not st.session_state.get("token"):
    st.error("🔒 You must be logged in to access this page.")
    st.markdown("Return to the main page and log in first.")
    st.stop()

user  = st.session_state.get("user", {})
token = st.session_state.get("token")

if user.get("role") not in ("admin", "staff"):
    st.error("🚫 Access denied. Admin or Staff role required.")
    st.stop()

st.title("🛠️ ChatDEVA Admin Panel")
st.caption(
    f"Logged in as **{user['username']}** · "
    f"{user['role'].capitalize()} · "
    f"College ID: {user['college_id']}"
)

# ── Tabs ──────────────────────────────────────────────────────────────
tab_docs, tab_users, tab_chats, tab_audit, tab_analytics = st.tabs([
    "📄 Documents",
    "👥 Users",
    "💬 Chat Monitor",
    "📋 Audit Log",
    "📊 Analytics",
])


# ─────────────────────────────────────────────────────────────────────
# TAB 1 — DOCUMENTS
# ─────────────────────────────────────────────────────────────────────
with tab_docs:
    st.subheader("Upload New Document")

    uploaded_file = st.file_uploader(
        "Choose a file (PDF, DOCX, TXT)",
        type=["pdf", "docx", "txt"],
        key="admin_upload",
    )
    doc_type = st.selectbox(
        "Document Type",
        ["notice", "syllabus", "timetable", "exam", "other"],
        key="doc_type_select",
    )

    if st.button("⚙️ Upload & Index", key="upload_btn"):
        if not uploaded_file:
            st.warning("Please select a file first.")
        else:
            with st.spinner(f"Uploading and indexing '{uploaded_file.name}'..."):
                resp = api_post(
                    "/documents/upload",
                    token=token,
                    data={"doc_type": doc_type},
                    files={"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)},
                )
            if resp.status_code == 201:
                doc = resp.json()
                st.success(
                    f"✅ '{doc['original_name']}' uploaded and indexed "
                    f"({doc['file_size_kb']:.1f} KB)"
                )
                st.rerun()
            else:
                st.error(f"❌ {resp.json().get('detail', 'Upload failed.')}")

    st.divider()
    st.subheader("Indexed Documents")

    docs_resp = api_get("/documents/", token=token)
    if docs_resp.status_code != 200:
        st.error("Could not load documents.")
    else:
        docs = docs_resp.json()
        if not docs:
            st.info("No documents uploaded yet.")
        else:
            for doc in docs:
                col1, col2, col3, col4, col5 = st.columns([4, 2, 2, 1, 1])
                with col1:
                    indexed_badge = "✅" if doc["is_indexed"] else "⏳"
                    st.markdown(f"{indexed_badge} **{doc['original_name']}**")
                with col2:
                    st.caption(doc["doc_type"])
                with col3:
                    st.caption(doc["created_at"][:10])
                with col4:
                    # Re-index button
                    if st.button("🔄", key=f"reindex_{doc['id']}", help="Re-index"):
                        with st.spinner("Re-indexing..."):
                            r = api_post(f"/documents/{doc['id']}/index", token=token)
                        if r.status_code == 200:
                            st.success("Re-indexed.")
                            st.rerun()
                        else:
                            st.error(r.json().get("detail", "Failed."))
                with col5:
                    if st.button("🗑️", key=f"del_doc_{doc['id']}", help="Delete"):
                        r = api_delete(f"/documents/{doc['id']}", token=token)
                        if r.status_code == 204:
                            st.success(f"Deleted '{doc['original_name']}'.")
                            st.rerun()
                        else:
                            st.error(r.json().get("detail", "Delete failed."))


# ─────────────────────────────────────────────────────────────────────
# TAB 2 — USERS (admin only)
# ─────────────────────────────────────────────────────────────────────
with tab_users:
    if user["role"] != "admin":
        st.info("User management is restricted to Admins only.")
    else:
        st.subheader("All Users in Your College")

        users_resp = api_get("/admin/users", token=token)
        if users_resp.status_code != 200:
            st.error("Could not load users.")
        else:
            users = users_resp.json()
            for u in users:
                col1, col2, col3, col4 = st.columns([3, 2, 3, 1])
                with col1:
                    active_badge = "🟢" if u["is_active"] else "🔴"
                    st.markdown(f"{active_badge} **{u['username']}**")
                with col2:
                    role_icon = {"admin": "👑", "staff": "🔧", "student": "🎓"}
                    st.caption(f"{role_icon.get(u['role'], '')} {u['role'].capitalize()}")
                with col3:
                    # Role change — only for other users
                    if u["id"] != user["id"] and u["is_active"]:
                        roles = ["student", "staff", "admin"]
                        new_role = st.selectbox(
                            "Role", roles,
                            index=roles.index(u["role"]),
                            key=f"role_sel_{u['id']}",
                            label_visibility="collapsed",
                        )
                        if new_role != u["role"]:
                            if st.button("Apply", key=f"role_btn_{u['id']}"):
                                r = api_patch(
                                    f"/admin/users/{u['id']}/role",
                                    token=token,
                                    json_data={"user_id": u["id"], "new_role": new_role},
                                )
                                if r.status_code == 200:
                                    st.success(f"Updated {u['username']} → {new_role}")
                                    st.rerun()
                                else:
                                    st.error(r.json().get("detail", "Failed."))
                    else:
                        st.caption("*(you)*" if u["id"] == user["id"] else "Inactive")
                with col4:
                    if u["id"] != user["id"] and u["is_active"]:
                        if st.button("🚫", key=f"deact_{u['id']}", help="Deactivate"):
                            r = api_delete(f"/admin/users/{u['id']}", token=token)
                            if r.status_code == 204:
                                st.warning(f"Deactivated {u['username']}.")
                                st.rerun()
                            else:
                                st.error(r.json().get("detail", "Failed."))

        st.divider()
        st.subheader("Create Admin / Staff Account")

        with st.form("create_user_form"):
            new_username = st.text_input("Username")
            new_password = st.text_input("Password", type="password")
            new_role     = st.selectbox("Role", ["staff", "admin"])
            submitted    = st.form_submit_button("➕ Create Account")

        if submitted:
            if not new_username or not new_password:
                st.warning("Fill in all fields.")
            else:
                r = api_post(
                    "/admin/users",
                    token=token,
                    json_data=None,
                    data=None,
                )
                # Use query params since this endpoint takes form fields
                r = requests.post(
                    f"{API}/admin/users",
                    headers={"Authorization": f"Bearer {token}"},
                    params={
                        "username": new_username,
                        "password": new_password,
                        "role":     new_role,
                    },
                )
                if r.status_code == 201:
                    st.success(f"✅ Created {new_role} account: {new_username}")
                    st.rerun()
                else:
                    st.error(r.json().get("detail", "Failed to create user."))


# ─────────────────────────────────────────────────────────────────────
# TAB 3 — CHAT MONITOR
# ─────────────────────────────────────────────────────────────────────
with tab_chats:
    st.subheader("All Chat Sessions in Your College")

    sessions_resp = api_get("/admin/chats", token=token)
    if sessions_resp.status_code != 200:
        st.error("Could not load sessions.")
    else:
        sessions = sessions_resp.json()
        if not sessions:
            st.info("No chat sessions yet.")
        else:
            # Group by user for readability
            selected_session = st.selectbox(
                "Select a session to view messages",
                options=[s["id"] for s in sessions],
                format_func=lambda sid: next(
                    (f"[{s['created_at'][:10]}] {s['title'][:50]}" for s in sessions if s["id"] == sid),
                    str(sid),
                ),
                key="monitor_session_select",
            )

            if selected_session:
                msgs_resp = api_get(f"/admin/chats/{selected_session}", token=token)
                if msgs_resp.status_code == 200:
                    msgs = msgs_resp.json()
                    st.markdown(f"**{len(msgs)} message(s)** in this session")
                    for msg in msgs:
                        icon = "🧑" if msg["role"] == "user" else "🤖"
                        with st.container():
                            st.markdown(f"{icon} **{msg['role'].capitalize()}:** {msg['content']}")
                            sources = json.loads(msg.get("sources", "[]"))
                            for src in sources:
                                st.caption(
                                    f"  ↳ 📘 {src.get('filename','')} "
                                    f"· {src.get('doc_type','')} "
                                    f"· {src.get('uploaded_at','')}"
                                )
                else:
                    st.error("Could not load messages.")


# ─────────────────────────────────────────────────────────────────────
# TAB 4 — AUDIT LOG
# ─────────────────────────────────────────────────────────────────────
with tab_audit:
    st.subheader("Recent Audit Events")
    st.markdown("Security log: logins, uploads, deletions, role changes.")

    audit_resp = api_get("/admin/audit?limit=100", token=token)
    if audit_resp.status_code != 200:
        st.error("Could not load audit log.")
    else:
        logs = audit_resp.json()
        if not logs:
            st.info("No audit events recorded yet.")
        else:
            for log in logs:
                col1, col2, col3 = st.columns([3, 4, 3])
                with col1:
                    st.caption(log["created_at"][:19])
                with col2:
                    st.markdown(f"`{log['action']}`")
                with col3:
                    st.caption(log.get("detail") or "—")


# ─────────────────────────────────────────────────────────────────────
# TAB 5 — ANALYTICS [PHASE 6]
# ─────────────────────────────────────────────────────────────────────
with tab_analytics:
    st.subheader("📊 Usage Analytics")
    st.markdown("Real-time insights into how students are using ChatDEVA.")

    analytics_resp = api_get("/admin/analytics", token=token)
    if analytics_resp.status_code != 200:
        st.error("Could not load analytics.")
    else:
        data = analytics_resp.json()

        # ── Top metrics row ───────────────────────────────────────────
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("👥 Total Users",     data.get("total_users", 0))
        with col2:
            st.metric("💬 Total Questions", data.get("total_questions", 0))
        with col3:
            st.metric("🗂️ Total Sessions",  data.get("total_sessions", 0))
        with col4:
            st.metric("📅 Queries Today",   data.get("queries_today", 0))

        st.divider()

        col_left, col_right = st.columns(2)

        # ── Most active users ─────────────────────────────────────────
        with col_left:
            st.subheader("🏆 Most Active Users")
            active_users = data.get("most_active_users", [])
            if not active_users:
                st.info("No activity yet.")
            else:
                for i, u in enumerate(active_users, 1):
                    st.markdown(
                        f"**{i}. {u['username']}** — "
                        f"`{u['questions']}` question(s)"
                    )

        # ── Top questions ─────────────────────────────────────────────
        with col_right:
            st.subheader("🔥 Most Asked Questions")
            top_qs = data.get("top_questions", [])
            if not top_qs:
                st.info("No questions yet.")
            else:
                for q in top_qs:
                    st.markdown(
                        f"- {q['question'][:80]}... "
                        f"*(asked {q['count']}x)*"
                    )

        st.divider()

        # ── Recent queries ────────────────────────────────────────────
        st.subheader("🕐 Recent Queries")
        recent = data.get("recent_queries", [])
        if not recent:
            st.info("No queries yet.")
        else:
            for q in recent:
                col_a, col_b = st.columns([5, 1])
                with col_a:
                    st.markdown(f"❓ {q['question']}")
                with col_b:
                    st.caption(q["asked_at"])
