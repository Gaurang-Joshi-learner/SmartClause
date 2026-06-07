import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import api from '../lib/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const setTokens = (access, refresh) => {
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
  }

  const clearTokens = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  const fetchMe = useCallback(async () => {
    try {
      const { data } = await api.get('/auth/me')
      setUser(data)
    } catch {
      clearTokens()
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (token) fetchMe()
    else setLoading(false)
  }, [fetchMe])

  const login = async (email, password) => {
    const { data } = await api.post('/auth/login', { email, password })
    setTokens(data.access_token, data.refresh_token)
    setUser(data.user)
    return data
  }

  const register = async (email, password, full_name, org_name) => {
    const { data } = await api.post('/auth/register', { email, password, full_name, org_name })
    setTokens(data.access_token, data.refresh_token)
    setUser(data.user)
    return data
  }

  const loginWithTokens = (access, refresh) => {
    setTokens(access, refresh)
    fetchMe()
  }

  const logout = () => {
    clearTokens()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, loginWithTokens }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
