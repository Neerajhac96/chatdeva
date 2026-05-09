/**
 * api/client.js — Centralised API layer
 * All backend calls go through here.
 * Token is automatically added from localStorage.
 * BACKEND_URL is set via environment variable.
 */

import axios from 'axios'

const BASE_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
})

// Auto-attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Auto-logout on 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// ── Auth ──────────────────────────────────────────────────────────────
export const authAPI = {
  login:     (data)    => api.post('/auth/login', data),
  register:  (data)    => api.post('/auth/register', data),
  me: (token) => api.get('/auth/me', {
    headers: token ? { Authorization: `Bearer ${token}` } : {}
  }),
  colleges:  ()        => api.get('/auth/colleges'),
  usage:     ()        => api.get('/auth/usage'),
  registerCollege: (data) => api.post('/auth/colleges/register', data),
}

// ── Chat ──────────────────────────────────────────────────────────────
export const chatAPI = {
  getSessions:    ()           => api.get('/chat/sessions'),
  createSession:  (title)      => api.post('/chat/sessions', { title }),
  deleteSession:  (id)         => api.delete(`/chat/sessions/${id}`),
  clearSessions:  ()           => api.delete('/chat/sessions'),
  getMessages:    (sessionId)  => api.get(`/chat/sessions/${sessionId}/messages`),
  ask:            (data)       => api.post('/chat/ask', data),
}

// ── Documents ─────────────────────────────────────────────────────────
export const docsAPI = {
  list:     ()              => api.get('/documents/'),
  upload:   (formData)      => api.post('/documents/upload', formData),
  delete:   (id)            => api.delete(`/documents/${id}`),
  reindex:  (id)            => api.post(`/documents/${id}/index`),
}

// ── Admin ─────────────────────────────────────────────────────────────
export const adminAPI = {
  getUsers:        ()           => api.get('/admin/users'),
  updateRole:      (data)       => api.patch(`/admin/users/${data.user_id}/role`, data),
  deactivateUser:  (id)         => api.delete(`/admin/users/${id}`),
  createUser:      (params)     => api.post('/admin/users', null, { params }),
  getChats:        ()           => api.get('/admin/chats'),
  getChatMessages: (id)         => api.get(`/admin/chats/${id}`),
  getAuditLog:     ()           => api.get('/admin/audit?limit=100'),
  getAnalytics:    ()           => api.get('/admin/analytics'),
}

export default api
