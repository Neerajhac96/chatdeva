import { useState, useEffect } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { authAPI } from '../api/client'

export default function Login() {
  const { login, user } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const [tab, setTab] = useState('login')

  // Separate loading states for login and register
  const [loginLoading,    setLoginLoading]    = useState(false)
  const [registerLoading, setRegisterLoading] = useState(false)
  const [collegesLoading, setCollegesLoading] = useState(true)

  const [colleges, setColleges] = useState([])
  const [error,    setError]    = useState('')
  const [success,  setSuccess]  = useState(location.state?.success || '')

  const [loginForm, setLoginForm] = useState({ username: '', password: '' })
  const [regForm,   setRegForm]   = useState({
    username: '', password: '', confirm: '', college_id: '',
  })

  // Redirect if already logged in
  useEffect(() => {
    if (user) navigate('/chat', { replace: true })
  }, [user, navigate])

  // Load colleges on mount — always needed for register tab
  useEffect(() => {
    setCollegesLoading(true)
    authAPI.colleges()
      .then(res => {
        setColleges(res.data)
        // Auto-select first college if only one exists
        if (res.data.length === 1) {
          setRegForm(prev => ({ ...prev, college_id: String(res.data[0].id) }))
        }
      })
      .catch(() => setError('Cannot reach backend. Make sure it is running.'))
      .finally(() => setCollegesLoading(false))
  }, [])

  // ── Login ──────────────────────────────────────────────────────────
  const handleLogin = async (e) => {
    e.preventDefault()
    setError('')
    setLoginLoading(true)
    try {
      await login(loginForm.username, loginForm.password)
      navigate('/chat', { replace: true })
    } catch (err) {
      setError(err.response?.data?.detail || 'Incorrect username or password.')
    } finally {
      setLoginLoading(false)
    }
  }

  // ── Register ───────────────────────────────────────────────────────
  const handleRegister = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')

    if (!regForm.username.trim()) {
      setError('Username cannot be empty.')
      return
    }
    if (!regForm.college_id) {
      setError('Please select your college.')
      return
    }
    if (regForm.password.length < 6) {
      setError('Password must be at least 6 characters.')
      return
    }
    if (regForm.password !== regForm.confirm) {
      setError('Passwords do not match.')
      return
    }

    setRegisterLoading(true)
    try {
      await authAPI.register({
        username:   regForm.username.trim(),
        password:   regForm.password,
        college_id: parseInt(regForm.college_id),
        role:       'student',
      })
      setSuccess('✅ Account created! Switch to Log In tab.')
      setRegForm({ username: '', password: '', confirm: '', college_id: '' })
    } catch (err) {
      setError(err.response?.data?.detail || 'Registration failed.')
    } finally {
      setRegisterLoading(false)
    }
  }

  const switchTab = (t) => {
    setTab(t)
    setError('')
    setSuccess('')
  }

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col items-center justify-center px-4">

      {/* Logo */}
      <Link to="/" className="flex items-center gap-2 mb-8">
        <span className="text-3xl">🎓</span>
        <span className="text-2xl font-bold text-white">ChatDEVA</span>
      </Link>

      <div className="w-full max-w-md bg-gray-900 rounded-2xl border border-gray-800 p-8">

        {/* Tabs */}
        <div className="flex rounded-xl bg-gray-800 p-1 mb-6">
          {[['login', '🔑 Log In'], ['register', '📝 Register']].map(([t, label]) => (
            <button key={t} onClick={() => switchTab(t)}
              className={`flex-1 py-2 rounded-lg text-sm font-medium transition ${
                tab === t
                  ? 'bg-indigo-600 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}>
              {label}
            </button>
          ))}
        </div>

        {/* Error / Success banners */}
        {error   && (
          <div className="bg-red-900/40 border border-red-700 text-red-300 rounded-lg px-4 py-2 mb-4 text-sm">
            ❌ {error}
          </div>
        )}
        {success && (
          <div className="bg-green-900/40 border border-green-700 text-green-300 rounded-lg px-4 py-2 mb-4 text-sm">
            {success}
          </div>
        )}

        {/* ── Login Form ── */}
        {tab === 'login' && (
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Username</label>
              <input
                type="text"
                value={loginForm.username}
                onChange={e => setLoginForm({ ...loginForm, username: e.target.value })}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-indigo-500 transition"
                placeholder="Enter your username"
                required
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Password</label>
              <input
                type="password"
                value={loginForm.password}
                onChange={e => setLoginForm({ ...loginForm, password: e.target.value })}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-indigo-500 transition"
                placeholder="Enter your password"
                required
              />
            </div>
            <button type="submit" disabled={loginLoading}
              className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white py-2.5 rounded-lg font-medium transition">
              {loginLoading ? 'Logging in...' : 'Log In →'}
            </button>
          </form>
        )}

        {/* ── Register Form ── */}
        {tab === 'register' && (
          <form onSubmit={handleRegister} className="space-y-4">

            {/* College dropdown */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-sm text-gray-400">Your College</label>

              </div>
              {collegesLoading ? (
                <div className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-gray-500 text-sm">
                  Loading colleges...
                </div>
              ) : colleges.length === 0 ? (
                <div className="w-full bg-gray-800 border border-red-700 rounded-lg px-4 py-2 text-red-400 text-sm">
                  No colleges available. Please contact the system administrator.
                </div>
              ) : (
                <select
                  value={regForm.college_id}
                  onChange={e => setRegForm({ ...regForm, college_id: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-indigo-500 transition"
                  required>
                  <option value="">Select your college</option>
                  {colleges.map(c => (
                    <option key={c.id} value={c.id}>
                      {c.name} ({c.code})
                    </option>
                  ))}
                </select>
              )}
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-1">Username</label>
              <input
                type="text"
                value={regForm.username}
                onChange={e => setRegForm({ ...regForm, username: e.target.value })}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-indigo-500 transition"
                placeholder="Choose a username"
                required
              />
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-1">Password</label>
              <input
                type="password"
                value={regForm.password}
                onChange={e => setRegForm({ ...regForm, password: e.target.value })}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-indigo-500 transition"
                placeholder="Min 6 characters"
                required
              />
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-1">Confirm Password</label>
              <input
                type="password"
                value={regForm.confirm}
                onChange={e => setRegForm({ ...regForm, confirm: e.target.value })}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-indigo-500 transition"
                placeholder="Repeat password"
                required
              />
            </div>

            <button type="submit" disabled={registerLoading || collegesLoading || colleges.length === 0}
              className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white py-2.5 rounded-lg font-medium transition">
              {registerLoading ? 'Creating account...' : 'Create Account →'}
            </button>
          </form>
        )}
      </div>

      <p className="mt-6 text-gray-600 text-sm">
        <Link to="/" className="hover:text-gray-400 transition">← Back to home</Link>
      </p>
    </div>
  )
}
