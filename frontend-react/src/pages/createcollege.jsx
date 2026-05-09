/**
 * CreateCollege.jsx — Invite-token protected college registration
 * Route: /create-college?token=XYZ
 *
 * [SECURITY] Token is read from URL query param.
 * Without a valid token, the form is blocked.
 * Token comes from super_admin via POST /admin/create-invite.
 */

import { useState, useEffect } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { authAPI } from '../api/client'

export default function CreateCollege() {
  const navigate      = useNavigate()
  const [searchParams] = useSearchParams()
  const token          = searchParams.get('token')

  const [loading,       setLoading]       = useState(false)
  const [tokenValid,    setTokenValid]     = useState(null)  // null=checking, true=ok, false=invalid
  const [error,         setError]         = useState('')
  const [form,          setForm]          = useState({
    name:           '',
    code:           '',
    contact_email:  '',
    admin_username: '',
    admin_password: '',
    confirm:        '',
  })

  // Validate token on mount by checking if it's present
  // Full validation happens server-side on submit
  useEffect(() => {
    if (!token) {
      setTokenValid(false)
    } else {
      setTokenValid(true)
    }
  }, [token])

  const update = (field) => (e) =>
    setForm(prev => ({ ...prev, [field]: e.target.value }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    if (form.admin_password.length < 6) {
      setError('Admin password must be at least 6 characters.')
      return
    }
    if (form.admin_password !== form.confirm) {
      setError('Passwords do not match.')
      return
    }

    setLoading(true)
    try {
      const res = await authAPI.registerCollege({
        invite_token:   token,          // [SECURITY] send token to backend
        name:           form.name.trim(),
        code:           form.code.trim().toUpperCase(),
        contact_email:  form.contact_email.trim(),
        admin_username: form.admin_username.trim(),
        admin_password: form.admin_password,
      })

      navigate('/login', {
        state: {
          success: `✅ "${res.data.college_name}" registered! Login with your admin credentials.`
        }
      })
    } catch (err) {
      const detail = err.response?.data?.detail || 'Registration failed.'
      // Show specific token errors prominently
      if (detail.toLowerCase().includes('invite') || detail.toLowerCase().includes('token')) {
        setTokenValid(false)
        setError(detail)
      } else {
        setError(detail)
      }
    } finally {
      setLoading(false)
    }
  }

  // ── No token in URL ───────────────────────────────────────────────
  if (tokenValid === false) {
    return (
      <div className="min-h-screen bg-gray-950 flex flex-col items-center justify-center px-4">
        <Link to="/" className="flex items-center gap-2 mb-8">
          <span className="text-3xl">🎓</span>
          <span className="text-2xl font-bold text-white">ChatDEVA</span>
        </Link>
        <div className="w-full max-w-md bg-gray-900 rounded-2xl border border-red-800 p-8 text-center">
          <div className="text-4xl mb-4">🔒</div>
          <h2 className="text-xl font-bold text-white mb-2">Invalid or Missing Invite</h2>
          <p className="text-gray-400 text-sm mb-6">
            {error || 'College registration requires a valid invite link. Please contact the system administrator to request an invite.'}
          </p>
          <Link to="/"
            className="inline-block bg-gray-800 hover:bg-gray-700 text-white px-6 py-2 rounded-lg text-sm transition">
            ← Back to Home
          </Link>
        </div>
      </div>
    )
  }

  // ── Checking token ────────────────────────────────────────────────
  if (tokenValid === null) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <p className="text-gray-500 animate-pulse">Validating invite...</p>
      </div>
    )
  }

  // ── Valid token — show registration form ──────────────────────────
  return (
    <div className="min-h-screen bg-gray-950 flex flex-col items-center justify-center px-4 py-12">
      <Link to="/" className="flex items-center gap-2 mb-2">
        <span className="text-3xl">🎓</span>
        <span className="text-2xl font-bold text-white">ChatDEVA</span>
      </Link>
      <p className="text-gray-500 text-sm mb-8">Set up your college's AI assistant</p>

      <div className="w-full max-w-lg bg-gray-900 rounded-2xl border border-gray-800 p-8">

        {/* Invite badge */}
        <div className="flex items-center gap-2 bg-green-900/20 border border-green-800 rounded-lg px-3 py-2 mb-6">
          <span className="text-green-400 text-sm">✅ Valid invite token</span>
          <span className="text-gray-600 text-xs ml-auto font-mono">{token?.slice(0, 8)}...</span>
        </div>

        <h1 className="text-xl font-bold text-white mb-1">Register Your College</h1>
        <p className="text-gray-500 text-sm mb-6">
          Create your college workspace. You'll get an admin account to manage documents and users.
        </p>

        {error && (
          <div className="bg-red-900/40 border border-red-700 text-red-300 rounded-lg px-4 py-3 mb-5 text-sm">
            ❌ {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">

          {/* College info */}
          <div className="bg-gray-800/50 rounded-xl p-4 space-y-4">
            <p className="text-xs text-gray-500 uppercase tracking-wider font-medium">
              College Information
            </p>
            <div>
              <label className="block text-sm text-gray-400 mb-1">College Name *</label>
              <input type="text" value={form.name} onChange={update('name')}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-indigo-500 transition"
                placeholder="e.g. ABES Engineering College" required />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">
                College Code *
                <span className="text-gray-600 ml-1 font-normal">(short unique ID)</span>
              </label>
              <input type="text" value={form.code} onChange={update('code')}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-indigo-500 transition uppercase"
                placeholder="e.g. ABESEC" maxLength={20} required />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Contact Email</label>
              <input type="email" value={form.contact_email} onChange={update('contact_email')}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-indigo-500 transition"
                placeholder="admin@yourcollege.ac.in" />
            </div>
          </div>

          {/* Admin account */}
          <div className="bg-gray-800/50 rounded-xl p-4 space-y-4">
            <p className="text-xs text-gray-500 uppercase tracking-wider font-medium">
              Admin Account
            </p>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Admin Username *</label>
              <input type="text" value={form.admin_username} onChange={update('admin_username')}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-indigo-500 transition"
                placeholder="Choose an admin username" required />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Admin Password *</label>
              <input type="password" value={form.admin_password} onChange={update('admin_password')}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-indigo-500 transition"
                placeholder="Min 6 characters" required />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Confirm Password *</label>
              <input type="password" value={form.confirm} onChange={update('confirm')}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-indigo-500 transition"
                placeholder="Repeat password" required />
            </div>
          </div>

          {/* Plan info */}
          <div className="bg-indigo-900/20 border border-indigo-800 rounded-xl p-4">
            <p className="text-indigo-400 font-medium text-sm">🎁 Free Plan</p>
            <p className="text-gray-400 text-xs mt-1">
              100 questions/student/month · Unlimited documents · Unlimited users
            </p>
          </div>

          <button type="submit" disabled={loading}
            className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white py-3 rounded-xl font-semibold transition">
            {loading ? 'Creating your workspace...' : '🚀 Register College →'}
          </button>
        </form>
      </div>

      <p className="mt-6 text-gray-600 text-sm">
        Already registered?{' '}
        <Link to="/login" className="text-indigo-400 hover:text-indigo-300 transition">Log in here</Link>
      </p>
    </div>
  )
}
