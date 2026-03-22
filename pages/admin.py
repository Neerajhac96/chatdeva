"""
pages/admin.py — Phase 6: Admin panel updated for ChromaDB
-----------------------------------------------------------
Changes from Phase 3:
  - Document delete now calls delete_document_from_index() to remove
    chunks from ChromaDB by source filename (no full index rebuild needed)
  - "Rebuild Index" button replaced by "Re-index All Documents" which
    re-processes files from disk into ChromaDB
  - All other tabs (Users, Chat Monitor) are unchanged

Folder structure:
    your_project/
    ├── app.py
    ├── rag_core.py
    ├── database.py
    └── pages/
        └── admin.py   ← this file
"""

import os
import streamlit as st

from database import (
    get_all_users,
    get_all_documents,
    get_all_chat_messages,
    promote_user,
    delete_user,
    delete_document_record,
    save_document_record,
)
from rag_core import (
    process_documents,
    load_faiss_index_if_exists,   # alias for load_vector_store_if_exists
    delete_document_from_index,   # [PHASE 6] new — deletes by source filename
    DOC_DIR,
    CHROMA_MODE,
)

st.set_page_config(page_title="ChatDEVA — Admin", layout="wide")

# ---------------------------------------------------------------------
# ACCESS CONTROL
# ---------------------------------------------------------------------
if "current_user" not in st.session_state or st.session_state.current_user is None:
    st.error("🔒 You must be logged in to access this page.")
    st.markdown("Please return to the main page and log in first.")
    st.stop()

user = st.session_state.current_user
if user.get("role") != "admin":
    st.error("🚫 Access Denied. This page is for admins only.")
    st.markdown(f"Your current role: **{user['role']}**")
    st.stop()

st.title("🛠️ ChatDEVA Admin Panel")
st.caption(
    f"Logged in as admin: **{user['username']}** "
    f"| Vector store: **ChromaDB ({CHROMA_MODE} mode)**"
)

if "faiss_db" not in st.session_state:
    st.session_state.faiss_db = load_faiss_index_if_exists()

# ---------------------------------------------------------------------
# TABS
# ---------------------------------------------------------------------
tab_docs, tab_users, tab_chats = st.tabs([
    "📄 Document Management",
    "👥 User Management",
    "💬 Chat Monitor",
])

# ─────────────────────────────────────────────────────────────────────
# TAB 1 — DOCUMENT MANAGEMENT
# ─────────────────────────────────────────────────────────────────────
with tab_docs:
    st.subheader("Upload New Documents")

    uploaded_files = st.file_uploader(
        "Choose files to add to the knowledge base",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
        key="admin_uploader",
    )

    if st.button("⚙️ Process & Index Documents", key="admin_process"):
        if uploaded_files:
            file_paths = []
            for uploaded_file in uploaded_files:
                file_name = uploaded_file.name
                base, ext = os.path.splitext(file_name)
                counter = 1
                file_path = os.path.join(DOC_DIR, file_name)
                while os.path.exists(file_path):
                    file_name = f"{base}_{counter}{ext}"
                    file_path = os.path.join(DOC_DIR, file_name)
                    counter += 1

                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                file_paths.append(file_path)

                save_document_record(
                    filename=os.path.basename(file_path),
                    original_name=uploaded_file.name,
                    user_id=user["id"],
                )

            with st.spinner("Indexing documents into ChromaDB..."):
                st.session_state.faiss_db, message = process_documents(file_paths)
            st.success(message)
        else:
            st.warning("Please select files first.")

    st.divider()
    st.subheader("Indexed Documents")

    docs = get_all_documents()
    if not docs:
        st.info("No documents in the knowledge base yet.")
    else:
        for doc in docs:
            col1, col2, col3 = st.columns([5, 2, 1])
            with col1:
                uploaded_at = doc["uploaded_at"]
                date_str = (
                    uploaded_at.strftime("%b %d, %Y %H:%M")
                    if hasattr(uploaded_at, "strftime")
                    else str(uploaded_at)
                )
                st.markdown(f"**{doc['original_name']}** — *{date_str}*")
            with col2:
                st.markdown(f"`ID: {doc['id']}`")
            with col3:
                if st.button("🗑️", key=f"del_doc_{doc['id']}", help="Delete document"):
                    # [PHASE 6] Delete chunks from ChromaDB by source filename
                    n_deleted = delete_document_from_index(doc["filename"])

                    # Delete the physical file
                    file_path = os.path.join(DOC_DIR, doc["filename"])
                    if os.path.exists(file_path):
                        os.remove(file_path)

                    # Remove DB record
                    delete_document_record(doc["id"])

                    if n_deleted > 0:
                        st.success(
                            f"✅ Deleted '{doc['original_name']}' "
                            f"({n_deleted} chunk(s) removed from ChromaDB)."
                        )
                    else:
                        st.warning(
                            f"Record deleted, but no chunks found in ChromaDB "
                            f"for '{doc['original_name']}'. "
                            "The file may not have been indexed yet."
                        )
                    st.rerun()

    st.divider()

    # [PHASE 6] Re-index replaces "Rebuild" — ChromaDB supports adding, not rebuilding
    st.subheader("Re-index All Documents")
    st.markdown(
        "Use this if you suspect the ChromaDB index is out of sync with the files "
        "in `uploaded_docs/`. This will re-add all files (duplicates are avoided "
        "via ChromaDB's ID system if you use consistent IDs — otherwise it adds again)."
    )
    if st.button("🔄 Re-index All Files from Disk"):
        remaining_files = [
            os.path.join(DOC_DIR, f)
            for f in os.listdir(DOC_DIR)
            if f.endswith((".pdf", ".txt", ".docx"))
        ]
        if remaining_files:
            with st.spinner("Re-indexing into ChromaDB..."):
                _, message = process_documents(remaining_files)
            st.success(message)
        else:
            st.warning("No files found in uploaded_docs/ to index.")


# ─────────────────────────────────────────────────────────────────────
# TAB 2 — USER MANAGEMENT (unchanged from Phase 3)
# ─────────────────────────────────────────────────────────────────────
with tab_users:
    st.subheader("All Registered Users")

    users = get_all_users()
    if not users:
        st.info("No users registered yet.")
    else:
        for u in users:
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            with col1:
                st.markdown(f"**{u['username']}**")
            with col2:
                role_badge = "👑 Admin" if u["role"] == "admin" else "🎓 Student"
                st.markdown(role_badge)
            with col3:
                if u["id"] != user["id"]:
                    new_role = "student" if u["role"] == "admin" else "admin"
                    if st.button(f"→ Make {new_role.capitalize()}", key=f"promote_{u['id']}"):
                        promote_user(u["id"], new_role)
                        st.success(f"Updated {u['username']} to {new_role}.")
                        st.rerun()
                else:
                    st.markdown("*(you)*")
            with col4:
                if u["id"] != user["id"]:
                    if st.button("🗑️", key=f"del_user_{u['id']}", help="Delete user"):
                        delete_user(u["id"])
                        st.warning(f"User '{u['username']}' deleted.")
                        st.rerun()

    st.divider()
    st.subheader("Create Admin User")
    new_admin_name = st.text_input("New admin username", key="new_admin_input")
    new_admin_pass = st.text_input("Password", type="password", key="new_admin_pass")
    if st.button("➕ Create Admin") and new_admin_name.strip() and new_admin_pass:
        from database import register_user
        new_u = register_user(new_admin_name.strip(), new_admin_pass, role="admin")
        if new_u:
            st.success(f"Admin user '{new_u['username']}' created.")
        else:
            st.error("Username already taken.")
        st.rerun()


# ─────────────────────────────────────────────────────────────────────
# TAB 3 — CHAT MONITOR (unchanged from Phase 3)
# ─────────────────────────────────────────────────────────────────────
with tab_chats:
    st.subheader("Recent Conversations (All Users)")
    st.markdown("Shows the last 200 messages across all users.")

    messages = get_all_chat_messages(limit=200)
    users_list = get_all_users()

    if not messages:
        st.info("No chat messages recorded yet.")
    else:
        current_uid = None
        for msg in messages:
            uid = msg.get("user_id", "unknown")
            if uid != current_uid:
                current_uid = uid
                username = next(
                    (u["username"] for u in users_list if u["id"] == uid),
                    f"User #{uid}",
                )
                created_at = msg["created_at"]
                date_str = (
                    created_at.strftime("%b %d, %H:%M")
                    if hasattr(created_at, "strftime")
                    else str(created_at)
                )
                st.markdown(f"---\n#### 👤 {username} — {date_str}")

            icon = "🧑" if msg["role"] == "user" else "🤖"
            st.markdown(f"{icon} **{msg['role'].capitalize()}:** {msg['content']}")
            for src in msg.get("sources", []):
                st.caption(f"  ↳ {src}")
