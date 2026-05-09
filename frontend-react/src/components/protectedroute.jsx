import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function ProtectedRoute({ children, adminOnly = false }) {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-950">
        <div className="text-gray-400 text-lg animate-pulse">Loading...</div>
      </div>
    )
  }

  if (!user) return <Navigate to="/login" replace />

  if (adminOnly && !['admin', 'staff'].includes(user.role)) {
    return <Navigate to="/chat" replace />
  }

  return children
}
