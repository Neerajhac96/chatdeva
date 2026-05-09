/**
 * AuthContext.jsx — Global authentication state
 * Provides user, token, login(), logout() to all components.
 * Token persisted in localStorage so login survives page refresh.
 */

import { createContext, useContext, useState, useEffect } from 'react'
import { authAPI } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user,    setUser]    = useState(null)
  const [token,   setToken]   = useState(localStorage.getItem('token'))
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const restore = async () => {
      const savedToken = localStorage.getItem('token')
      if (savedToken) {
        try {
          const res = await authAPI.me(savedToken)  // ← pass token
          setUser(res.data)
        } catch {
          localStorage.removeItem('token')
          localStorage.removeItem('user')
          setToken(null)
        }
      }
      setLoading(false)
    }
    restore()
  }, [])

  const login = async (username, password) => {
    const res = await authAPI.login({ username, password })
    const tok = res.data.access_token

    localStorage.setItem('token', tok)
    setToken(tok)

    const meRes = await authAPI.me(tok)  // ← pass token directly
    setUser(meRes.data)
    return meRes.data
  }

  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, token, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
