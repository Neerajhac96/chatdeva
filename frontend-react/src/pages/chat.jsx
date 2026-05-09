import { useState, useEffect, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { chatAPI, authAPI } from '../api/client'

export default function Chat() {
  const { user, logout }              = useAuth()
  const navigate                      = useNavigate()
  const bottomRef                     = useRef(null)

  const [sessions,   setSessions]     = useState([])
  const [activeId,   setActiveId]     = useState(null)
  const [messages,   setMessages]     = useState([])
  const [input,      setInput]        = useState('')
  const [loading,    setLoading]      = useState(false)
  const [usage,      setUsage]        = useState(null)
  const [sidebarOpen, setSidebarOpen] = useState(true)

  // Load sessions on mount
  useEffect(() => {
    loadSessions()
    if (user?.role === 'student') loadUsage()
  }, [])

  // Scroll to bottom when messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const loadSessions = async () => {
    try {
      const res = await chatAPI.getSessions()
      setSessions(res.data)
    } catch {}
  }

  const loadUsage = async () => {
    try {
      const res = await authAPI.usage()
      setUsage(res.data)
    } catch {}
  }

  const newChat = async () => {
    try {
      const res = await chatAPI.createSession('New Chat')
      const session = res.data
      setSessions(prev => [session, ...prev])
      setActiveId(session.id)
      setMessages([])
    } catch {}
  }

  const loadSession = async (sessionId) => {
    setActiveId(sessionId)
    try {
      const res = await chatAPI.getMessages(sessionId)
      setMessages(res.data.map(m => ({
        role:    m.role,
        content: m.content,
        sources: JSON.parse(m.sources || '[]'),
      })))
    } catch {}
  }

  const deleteSession = async (e, sessionId) => {
    e.stopPropagation()
    try {
      await chatAPI.deleteSession(sessionId)
      setSessions(prev => prev.filter(s => s.id !== sessionId))
      if (activeId === sessionId) {
        setActiveId(null)
        setMessages([])
      }
    } catch {}
  }

  const sendMessage = async (e) => {
    e.preventDefault()
    if (!input.trim() || loading) return
    if (!activeId) {
      await newChat()
      return
    }

    const query = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: query, sources: [] }])
    setLoading(true)

    try {
      const res = await chatAPI.ask({ session_id: activeId, query })
      const { answer, sources } = res.data
      setMessages(prev => [...prev, { role: 'assistant', content: answer, sources }])

      // Update session title from first message
      setSessions(prev => prev.map(s =>
        s.id === activeId && s.title === 'New Chat'
          ? { ...s, title: query.slice(0, 40) }
          : s
      ))

      // Refresh usage
      if (user?.role === 'student') loadUsage()
    } catch (err) {
      const detail = err.response?.data?.detail || 'Something went wrong.'
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `⚠️ ${detail}`,
        sources: [],
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  return (
    <div className="flex h-screen bg-gray-950 text-white overflow-hidden">

      {/* ── Sidebar ── */}
      <aside className={`${sidebarOpen ? 'w-64' : 'w-0'} transition-all duration-200 flex-shrink-0 bg-gray-900 border-r border-gray-800 flex flex-col overflow-hidden`}>

        {/* Logo */}
        <div className="p-4 border-b border-gray-800">
          <Link to="/" className="flex items-center gap-2">
            <span className="text-xl">🎓</span>
            <span className="font-bold text-white">ChatDEVA</span>
          </Link>
        </div>

        {/* New Chat */}
        <div className="p-3">
          <button onClick={newChat}
            className="w-full flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-2 rounded-lg text-sm font-medium transition">
            <span className="text-lg">+</span> New Chat
          </button>
        </div>

        {/* Sessions list */}
        <div className="flex-1 overflow-y-auto px-2 space-y-1">
          {sessions.map(s => (
            <div key={s.id}
              onClick={() => loadSession(s.id)}
              className={`group flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer text-sm transition ${
                activeId === s.id
                  ? 'bg-gray-700 text-white'
                  : 'text-gray-400 hover:bg-gray-800 hover:text-white'
              }`}>
              <span className="truncate flex-1">
                {activeId === s.id && '▶ '}
                {s.title}
              </span>
              <button
                onClick={(e) => deleteSession(e, s.id)}
                className="opacity-0 group-hover:opacity-100 text-gray-500 hover:text-red-400 ml-1 transition">
                ×
              </button>
            </div>
          ))}
        </div>

        {/* Bottom section */}
        <div className="border-t border-gray-800 p-3 space-y-2">

          {/* Usage meter — students only */}
          {user?.role === 'student' && usage && (
            <div className="bg-gray-800 rounded-lg p-3">
              <div className="flex justify-between text-xs text-gray-400 mb-1">
                <span>📊 Usage</span>
                <span>{usage.used}/{usage.monthly_limit}</span>
              </div>
              <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${
                    usage.remaining === 0 ? 'bg-red-500' : 'bg-indigo-500'
                  }`}
                  style={{ width: `${Math.min((usage.used / usage.monthly_limit) * 100, 100)}%` }}
                />
              </div>
              <p className="text-xs text-gray-500 mt-1">{usage.remaining} questions remaining</p>
            </div>
          )}

          {/* Admin panel link */}
          {['admin', 'staff'].includes(user?.role) && (
            <Link to="/admin"
              className="flex items-center gap-2 text-gray-400 hover:text-white text-sm px-2 py-1.5 rounded-lg hover:bg-gray-800 transition">
              🛠️ Admin Panel
            </Link>
          )}

          {/* User info + logout */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 min-w-0">
              <div className="w-7 h-7 bg-indigo-700 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0">
                {user?.username?.[0]?.toUpperCase()}
              </div>
              <div className="min-w-0">
                <p className="text-sm text-white truncate">{user?.username}</p>
                <p className="text-xs text-gray-500 capitalize">{user?.role}</p>
              </div>
            </div>
            <button onClick={handleLogout}
              className="text-gray-500 hover:text-white text-xs px-2 py-1 rounded hover:bg-gray-800 transition flex-shrink-0">
              Out
            </button>
          </div>
        </div>
      </aside>

      {/* ── Main chat area ── */}
      <main className="flex-1 flex flex-col min-w-0">

        {/* Top bar */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-800">
          <button onClick={() => setSidebarOpen(o => !o)}
            className="text-gray-400 hover:text-white transition p-1">
            ☰
          </button>
          <span className="text-gray-300 text-sm truncate">
            {activeId
              ? sessions.find(s => s.id === activeId)?.title || 'Chat'
              : 'ChatDEVA'}
          </span>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto py-6 px-4 space-y-6">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="text-5xl mb-4">🎓</div>
              <h2 className="text-2xl font-semibold text-white mb-2">
                How can I help you?
              </h2>
              <p className="text-gray-500 max-w-sm">
                Ask anything about your college — syllabus, exams, notices, timetables.
              </p>
              <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-lg">
                {[
                  'What topics are in the syllabus?',
                  'When is the next exam?',
                  'Any recent notices?',
                  'What is the timetable?',
                ].map(q => (
                  <button key={q}
                    onClick={() => setInput(q)}
                    className="bg-gray-800 hover:bg-gray-700 border border-gray-700 text-gray-300 text-sm px-4 py-3 rounded-xl text-left transition">
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {msg.role === 'assistant' && (
                <div className="w-8 h-8 bg-indigo-700 rounded-full flex items-center justify-center text-sm flex-shrink-0 mt-1">
                  🎓
                </div>
              )}
              <div className={`max-w-2xl ${msg.role === 'user' ? 'order-first' : ''}`}>
                <div className={`px-4 py-3 rounded-2xl text-sm leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-indigo-600 text-white rounded-tr-sm ml-auto'
                    : 'bg-gray-800 text-gray-200 rounded-tl-sm'
                }`}>
                  {msg.content}
                </div>
                {msg.sources?.length > 0 && (
                  <div className="mt-2 space-y-1">
                    {msg.sources.map((src, j) => (
                      <div key={j} className="flex items-center gap-2 text-xs text-indigo-400">
                        <span>📘</span>
                        <span>{src.filename}</span>
                        <span className="text-gray-600">·</span>
                        <span className="text-gray-500">{src.doc_type}</span>
                        <span className="text-gray-600">·</span>
                        <span className="text-gray-500">{src.uploaded_at}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              {msg.role === 'user' && (
                <div className="w-8 h-8 bg-gray-700 rounded-full flex items-center justify-center text-sm flex-shrink-0 mt-1">
                  {user?.username?.[0]?.toUpperCase()}
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className="flex gap-3">
              <div className="w-8 h-8 bg-indigo-700 rounded-full flex items-center justify-center text-sm flex-shrink-0">
                🎓
              </div>
              <div className="bg-gray-800 px-4 py-3 rounded-2xl rounded-tl-sm">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{animationDelay:'0ms'}} />
                  <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{animationDelay:'150ms'}} />
                  <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{animationDelay:'300ms'}} />
                </div>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="p-4 border-t border-gray-800">
          <form onSubmit={sendMessage}
            className="flex gap-3 bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 focus-within:border-indigo-500 transition">
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="Ask a question about your college documents..."
              className="flex-1 bg-transparent text-white placeholder-gray-500 focus:outline-none text-sm"
              disabled={loading}
            />
            <button type="submit"
              disabled={loading || !input.trim()}
              className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white w-8 h-8 rounded-lg flex items-center justify-center transition flex-shrink-0">
              ↑
            </button>
          </form>
          <p className="text-center text-xs text-gray-600 mt-2">
            Answers are based on your college's uploaded documents only.
          </p>
        </div>
      </main>
    </div>
  )
}
