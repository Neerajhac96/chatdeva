import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { adminAPI, docsAPI } from '../api/client'

const TABS = ['📊 Analytics', '📄 Documents', '👥 Users', '💬 Chats', '📋 Audit', '🔑 Invites']

export default function Admin() {
  const { user } = useAuth()
  const [tab, setTab] = useState(0)

  return (
    <div className="min-h-screen bg-gray-950 text-white">

      {/* Top nav */}
      <nav className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
        <div className="flex items-center gap-4">
          <Link to="/" className="flex items-center gap-2">
            <span className="text-xl">🎓</span>
            <span className="font-bold">ChatDEVA</span>
          </Link>
          <span className="text-gray-600">/</span>
          <span className="text-gray-400 text-sm">Admin Panel</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-400">
            👑 {user?.username}
          </span>
          <Link to="/chat"
            className="text-sm text-indigo-400 hover:text-indigo-300 transition">
            ← Back to Chat
          </Link>
        </div>
      </nav>

      {/* Tab bar */}
      <div className="flex gap-1 px-6 pt-4 border-b border-gray-800 overflow-x-auto">
        {TABS.map((t, i) => (
          <button key={t} onClick={() => setTab(i)}
            className={`px-4 py-2 text-sm font-medium rounded-t-lg transition whitespace-nowrap ${
              tab === i
                ? 'bg-gray-900 text-white border border-b-0 border-gray-700'
                : 'text-gray-500 hover:text-gray-300'
            }`}>
            {t}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="p-6">
        {tab === 0 && <AnalyticsTab />}
        {tab === 1 && <DocumentsTab />}
        {tab === 2 && <UsersTab />}
        {tab === 3 && <ChatsTab />}
        {tab === 4 && <AuditTab />}
        {tab === 5 && <InvitesTab />}
      </div>
    </div>
  )
}

// ── Analytics Tab ────────────────────────────────────────────────────
function AnalyticsTab() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    adminAPI.getAnalytics()
      .then(res => setData(res.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <LoadingSpinner />
  if (!data)   return <ErrorMsg msg="Could not load analytics." />

  return (
    <div className="space-y-6">
      {/* Metric cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Total Users',     value: data.total_users,     icon: '👥' },
          { label: 'Total Questions', value: data.total_questions, icon: '💬' },
          { label: 'Sessions',        value: data.total_sessions,  icon: '🗂️' },
          { label: 'Today',           value: data.queries_today,   icon: '📅' },
        ].map(m => (
          <div key={m.label} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <div className="text-2xl mb-1">{m.icon}</div>
            <div className="text-3xl font-bold">{m.value}</div>
            <div className="text-sm text-gray-500 mt-1">{m.label}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Most active users */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h3 className="font-semibold mb-4">🏆 Most Active Users</h3>
          {data.most_active_users.length === 0
            ? <p className="text-gray-500 text-sm">No activity yet.</p>
            : data.most_active_users.map((u, i) => (
              <div key={u.username} className="flex items-center justify-between py-2 border-b border-gray-800 last:border-0">
                <div className="flex items-center gap-3">
                  <span className="text-gray-500 text-sm w-5">{i + 1}.</span>
                  <span className="text-sm">{u.username}</span>
                </div>
                <span className="text-indigo-400 text-sm font-medium">{u.questions}q</span>
              </div>
            ))
          }
        </div>

        {/* Top questions */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h3 className="font-semibold mb-4">🔥 Most Asked Questions</h3>
          {data.top_questions.length === 0
            ? <p className="text-gray-500 text-sm">No questions yet.</p>
            : data.top_questions.map((q, i) => (
              <div key={i} className="flex items-start justify-between py-2 border-b border-gray-800 last:border-0 gap-3">
                <p className="text-sm text-gray-300 truncate flex-1">{q.question}</p>
                <span className="text-xs text-gray-500 flex-shrink-0">{q.count}×</span>
              </div>
            ))
          }
        </div>
      </div>

      {/* Recent queries */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h3 className="font-semibold mb-4">🕐 Recent Queries</h3>
        {data.recent_queries.length === 0
          ? <p className="text-gray-500 text-sm">No queries yet.</p>
          : data.recent_queries.map((q, i) => (
            <div key={i} className="flex items-center justify-between py-2 border-b border-gray-800 last:border-0">
              <p className="text-sm text-gray-300 truncate flex-1">❓ {q.question}</p>
              <span className="text-xs text-gray-600 flex-shrink-0 ml-4">{q.asked_at}</span>
            </div>
          ))
        }
      </div>
    </div>
  )
}

// ── Documents Tab ────────────────────────────────────────────────────
function DocumentsTab() {
  const [docs,    setDocs]    = useState([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [file,    setFile]    = useState(null)
  const [docType, setDocType] = useState('other')
  const [msg,     setMsg]     = useState('')

  useEffect(() => { loadDocs() }, [])

  const loadDocs = () => {
    docsAPI.list()
      .then(res => setDocs(res.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  const handleUpload = async (e) => {
    e.preventDefault()
    if (!file) return
    setUploading(true)
    setMsg('')
    const form = new FormData()
    form.append('file', file)
    form.append('doc_type', docType)
    try {
      await docsAPI.upload(form)
      setMsg('✅ Document uploaded and indexed.')
      setFile(null)
      loadDocs()
    } catch (err) {
      setMsg('❌ ' + (err.response?.data?.detail || 'Upload failed.'))
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = async (id, name) => {
    if (!confirm(`Delete "${name}"?`)) return
    try {
      await docsAPI.delete(id)
      setDocs(prev => prev.filter(d => d.id !== id))
    } catch {}
  }

  return (
    <div className="space-y-6">
      {/* Upload form */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h3 className="font-semibold mb-4">Upload Document</h3>
        {msg && (
          <div className={`text-sm px-3 py-2 rounded-lg mb-3 ${
            msg.startsWith('✅') ? 'bg-green-900/40 text-green-300' : 'bg-red-900/40 text-red-300'
          }`}>{msg}</div>
        )}
        <form onSubmit={handleUpload} className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="block text-xs text-gray-400 mb-1">File (PDF, DOCX, TXT)</label>
            <input type="file" accept=".pdf,.docx,.txt"
              onChange={e => setFile(e.target.files[0])}
              className="text-sm text-gray-300 file:mr-3 file:bg-indigo-600 file:text-white file:border-0 file:rounded-lg file:px-3 file:py-1.5 file:cursor-pointer" />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Document Type</label>
            <select value={docType} onChange={e => setDocType(e.target.value)}
              className="bg-gray-800 border border-gray-700 text-white text-sm rounded-lg px-3 py-2">
              {['notice','syllabus','timetable','exam','other'].map(t => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
          <button type="submit" disabled={uploading || !file}
            className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white text-sm px-4 py-2 rounded-lg transition">
            {uploading ? 'Uploading...' : '⚙️ Upload & Index'}
          </button>
        </form>
      </div>

      {/* Documents list */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <div className="p-4 border-b border-gray-800">
          <h3 className="font-semibold">Indexed Documents ({docs.length})</h3>
        </div>
        {loading ? <LoadingSpinner /> : docs.length === 0
          ? <p className="text-gray-500 text-sm p-4">No documents uploaded yet.</p>
          : (
            <table className="w-full text-sm">
              <thead className="bg-gray-800">
                <tr>
                  {['Name','Type','Size','Date','Indexed',''].map(h => (
                    <th key={h} className="text-left text-gray-400 px-4 py-2 font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {docs.map(doc => (
                  <tr key={doc.id} className="border-t border-gray-800 hover:bg-gray-800/50">
                    <td className="px-4 py-3 text-gray-200">{doc.original_name}</td>
                    <td className="px-4 py-3">
                      <span className="bg-indigo-900/40 text-indigo-300 text-xs px-2 py-0.5 rounded">
                        {doc.doc_type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-500">{doc.file_size_kb?.toFixed(1)} KB</td>
                    <td className="px-4 py-3 text-gray-500">{doc.created_at?.slice(0,10)}</td>
                    <td className="px-4 py-3">
                      {doc.is_indexed
                        ? <span className="text-green-400">✅</span>
                        : <span className="text-yellow-400">⏳</span>}
                    </td>
                    <td className="px-4 py-3">
                      <button onClick={() => handleDelete(doc.id, doc.original_name)}
                        className="text-gray-500 hover:text-red-400 transition text-xs">
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )
        }
      </div>
    </div>
  )
}

// ── Users Tab ─────────────────────────────────────────────────────────
function UsersTab() {
  const { user: me } = useAuth()
  const [users,   setUsers]   = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    adminAPI.getUsers()
      .then(res => setUsers(res.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const changeRole = async (userId, newRole) => {
    try {
      await adminAPI.updateRole({ user_id: userId, new_role: newRole })
      setUsers(prev => prev.map(u => u.id === userId ? { ...u, role: newRole } : u))
    } catch {}
  }

  const deactivate = async (userId, username) => {
    if (!confirm(`Deactivate ${username}?`)) return
    try {
      await adminAPI.deactivateUser(userId)
      setUsers(prev => prev.map(u => u.id === userId ? { ...u, is_active: false } : u))
    } catch {}
  }

  if (loading) return <LoadingSpinner />

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      <div className="p-4 border-b border-gray-800">
        <h3 className="font-semibold">All Users ({users.length})</h3>
      </div>
      <table className="w-full text-sm">
        <thead className="bg-gray-800">
          <tr>
            {['Username','Role','Status','Joined','Actions'].map(h => (
              <th key={h} className="text-left text-gray-400 px-4 py-2 font-medium">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {users.map(u => (
            <tr key={u.id} className="border-t border-gray-800 hover:bg-gray-800/50">
              <td className="px-4 py-3 text-gray-200 font-medium">
                {u.username}
                {u.id === me?.id && <span className="ml-2 text-xs text-gray-500">(you)</span>}
              </td>
              <td className="px-4 py-3">
                <span className={`text-xs px-2 py-0.5 rounded capitalize ${
                  u.role === 'admin' ? 'bg-yellow-900/40 text-yellow-300' :
                  u.role === 'staff' ? 'bg-blue-900/40 text-blue-300' :
                  'bg-gray-700 text-gray-300'
                }`}>{u.role}</span>
              </td>
              <td className="px-4 py-3">
                {u.is_active
                  ? <span className="text-green-400 text-xs">Active</span>
                  : <span className="text-red-400 text-xs">Inactive</span>}
              </td>
              <td className="px-4 py-3 text-gray-500 text-xs">{u.created_at?.slice(0,10)}</td>
              <td className="px-4 py-3">
                {u.id !== me?.id && u.is_active && (
                  <div className="flex gap-2">
                    <select
                      defaultValue={u.role}
                      onChange={e => changeRole(u.id, e.target.value)}
                      className="bg-gray-800 border border-gray-700 text-gray-300 text-xs rounded px-2 py-1">
                      <option value="student">Student</option>
                      <option value="staff">Staff</option>
                      <option value="admin">Admin</option>
                    </select>
                    <button onClick={() => deactivate(u.id, u.username)}
                      className="text-gray-500 hover:text-red-400 text-xs transition">
                      Deactivate
                    </button>
                  </div>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── Chats Tab ─────────────────────────────────────────────────────────
function ChatsTab() {
  const [sessions,  setSessions]  = useState([])
  const [selected,  setSelected]  = useState(null)
  const [messages,  setMessages]  = useState([])
  const [loading,   setLoading]   = useState(true)

  useEffect(() => {
    adminAPI.getChats()
      .then(res => setSessions(res.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const viewSession = async (id) => {
    setSelected(id)
    try {
      const res = await adminAPI.getChatMessages(id)
      setMessages(res.data)
    } catch {}
  }

  if (loading) return <LoadingSpinner />

  return (
    <div className="flex gap-4 h-96">
      {/* Session list */}
      <div className="w-64 bg-gray-900 border border-gray-800 rounded-xl overflow-y-auto flex-shrink-0">
        <div className="p-3 border-b border-gray-800 text-sm font-medium">
          Sessions ({sessions.length})
        </div>
        {sessions.map(s => (
          <div key={s.id} onClick={() => viewSession(s.id)}
            className={`px-3 py-2 cursor-pointer text-sm border-b border-gray-800 hover:bg-gray-800 transition ${
              selected === s.id ? 'bg-gray-800 text-white' : 'text-gray-400'
            }`}>
            <p className="truncate">{s.title}</p>
            <p className="text-xs text-gray-600">{s.created_at?.slice(0,10)}</p>
          </div>
        ))}
      </div>

      {/* Messages */}
      <div className="flex-1 bg-gray-900 border border-gray-800 rounded-xl overflow-y-auto p-4 space-y-3">
        {!selected
          ? <p className="text-gray-500 text-sm text-center mt-10">Select a session to view messages</p>
          : messages.map((m, i) => (
            <div key={i} className={`flex gap-2 ${m.role === 'user' ? 'justify-end' : ''}`}>
              <div className={`text-sm px-3 py-2 rounded-xl max-w-sm ${
                m.role === 'user'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-800 text-gray-300'
              }`}>
                {m.content}
              </div>
            </div>
          ))
        }
      </div>
    </div>
  )
}

// ── Audit Tab ─────────────────────────────────────────────────────────
function AuditTab() {
  const [logs,    setLogs]    = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    adminAPI.getAuditLog()
      .then(res => setLogs(res.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <LoadingSpinner />

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      <div className="p-4 border-b border-gray-800">
        <h3 className="font-semibold">Audit Log ({logs.length} events)</h3>
      </div>
      <table className="w-full text-sm">
        <thead className="bg-gray-800">
          <tr>
            {['Time','Action','Detail','IP'].map(h => (
              <th key={h} className="text-left text-gray-400 px-4 py-2 font-medium">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {logs.map(log => (
            <tr key={log.id} className="border-t border-gray-800 hover:bg-gray-800/50">
              <td className="px-4 py-2 text-gray-500 text-xs whitespace-nowrap">
                {log.created_at?.slice(0,19).replace('T',' ')}
              </td>
              <td className="px-4 py-2">
                <code className="bg-gray-800 text-indigo-300 text-xs px-2 py-0.5 rounded">
                  {log.action}
                </code>
              </td>
              <td className="px-4 py-2 text-gray-400 text-xs">{log.detail || '—'}</td>
              <td className="px-4 py-2 text-gray-600 text-xs">{log.ip_address || '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── Helpers ───────────────────────────────────────────────────────────
function LoadingSpinner() {
  return (
    <div className="flex justify-center py-12">
      <div className="text-gray-500 animate-pulse">Loading...</div>
    </div>
  )
}

function ErrorMsg({ msg }) {
  return <div className="text-red-400 text-sm p-4">{msg}</div>
}

// ── Invites Tab (super_admin only) ───────────────────────────────────
function InvitesTab() {
  const { user } = useAuth()
  const [invites,  setInvites]  = useState([])
  const [loading,  setLoading]  = useState(true)
  const [creating, setCreating] = useState(false)
  const [email,    setEmail]    = useState('')
  const [days,     setDays]     = useState(7)
  const [result,   setResult]   = useState(null)
  const [error,    setError]    = useState('')

  const isSuperAdmin = user?.role === 'super_admin'

  useEffect(() => {
    if (isSuperAdmin) {
      fetch(`${import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'}/admin/invites`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
      })
        .then(r => r.json())
        .then(setInvites)
        .catch(() => {})
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [isSuperAdmin])

  const createInvite = async (e) => {
    e.preventDefault()
    setCreating(true)
    setResult(null)
    setError('')
    try {
      const params = new URLSearchParams()
      if (email) params.append('email', email)
      params.append('expires_days', days)

      const resp = await fetch(
        `${import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'}/admin/create-invite?${params}`,
        {
          method: 'POST',
          headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
        }
      )
      if (!resp.ok) {
        const err = await resp.json()
        setError(err.detail || 'Failed to create invite.')
        return
      }
      const data = await resp.json()
      setResult(data)
      setEmail('')
      // Refresh list
      const listResp = await fetch(
        `${import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'}/admin/invites`,
        { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }
      )
      setInvites(await listResp.json())
    } catch {
      setError('Network error.')
    } finally {
      setCreating(false)
    }
  }

  if (!isSuperAdmin) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center">
        <div className="text-4xl mb-3">🔒</div>
        <h3 className="text-lg font-semibold text-white mb-2">Super Admin Only</h3>
        <p className="text-gray-500 text-sm">
          Only the system super_admin can create college invites.
          Your role: <span className="text-indigo-400">{user?.role}</span>
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">

      {/* Create invite form */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <h3 className="font-semibold text-white mb-1">🔑 Create College Invite</h3>
        <p className="text-gray-500 text-sm mb-4">
          Generate a one-time invite link. Share it with a college admin to let them register.
        </p>

        {error && (
          <div className="bg-red-900/40 border border-red-700 text-red-300 rounded-lg px-4 py-2 mb-4 text-sm">
            ❌ {error}
          </div>
        )}

        {result && (
          <div className="bg-green-900/20 border border-green-700 rounded-xl p-4 mb-4">
            <p className="text-green-400 text-sm font-medium mb-2">✅ Invite created!</p>
            <p className="text-xs text-gray-400 mb-1">Share this link with the college admin:</p>
            <div className="bg-gray-800 rounded-lg p-3 flex items-center gap-2">
              <code className="text-indigo-300 text-xs flex-1 break-all">
                {result.invite_url}
              </code>
              <button
                onClick={() => navigator.clipboard.writeText(result.invite_url)}
                className="text-xs bg-indigo-600 hover:bg-indigo-500 text-white px-2 py-1 rounded transition flex-shrink-0">
                Copy
              </button>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Expires: {result.expires_at} · Token: {result.token.slice(0, 12)}...
            </p>
          </div>
        )}

        <form onSubmit={createInvite} className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="block text-xs text-gray-400 mb-1">Email (optional)</label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="college@example.com"
              className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500 w-56"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Expires in (days)</label>
            <select
              value={days}
              onChange={e => setDays(Number(e.target.value))}
              className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm">
              <option value={1}>1 day</option>
              <option value={3}>3 days</option>
              <option value={7}>7 days</option>
              <option value={30}>30 days</option>
            </select>
          </div>
          <button type="submit" disabled={creating}
            className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-lg transition">
            {creating ? 'Creating...' : '+ Generate Invite'}
          </button>
        </form>
      </div>

      {/* Invite history */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <div className="p-4 border-b border-gray-800">
          <h3 className="font-semibold">Invite History ({invites.length})</h3>
        </div>
        {loading ? <LoadingSpinner /> : invites.length === 0
          ? <p className="text-gray-500 text-sm p-4">No invites created yet.</p>
          : (
            <table className="w-full text-sm">
              <thead className="bg-gray-800">
                <tr>
                  {['Token', 'Email', 'Status', 'Expires', 'Created'].map(h => (
                    <th key={h} className="text-left text-gray-400 px-4 py-2 font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {invites.map(inv => (
                  <tr key={inv.id} className="border-t border-gray-800 hover:bg-gray-800/50">
                    <td className="px-4 py-2 font-mono text-xs text-gray-400">{inv.token}</td>
                    <td className="px-4 py-2 text-gray-400 text-xs">{inv.email || '—'}</td>
                    <td className="px-4 py-2">
                      {inv.is_used
                        ? <span className="text-xs bg-gray-700 text-gray-400 px-2 py-0.5 rounded">Used</span>
                        : <span className="text-xs bg-green-900/40 text-green-400 px-2 py-0.5 rounded">Active</span>
                      }
                    </td>
                    <td className="px-4 py-2 text-gray-500 text-xs">{inv.expires_at}</td>
                    <td className="px-4 py-2 text-gray-500 text-xs">{inv.created_at}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )
        }
      </div>
    </div>
  )
}
