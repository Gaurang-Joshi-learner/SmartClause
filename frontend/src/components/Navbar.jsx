import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { FileText, Upload, LayoutDashboard, LogOut, ChevronDown } from 'lucide-react'
import { useState } from 'react'
import clsx from 'clsx'

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [dropdownOpen, setDropdownOpen] = useState(false)

  const handleLogout = () => { logout(); navigate('/login') }
  const isActive = (path) => location.pathname === path

  return (
    <nav className="bg-white border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/dashboard" className="flex items-center gap-2">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <FileText className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-gray-900 text-lg">SmartClause</span>
          </Link>

          {/* Nav links */}
          <div className="flex items-center gap-1">
            <Link to="/dashboard" className={clsx(
              'flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
              isActive('/dashboard') ? 'bg-blue-50 text-blue-700' : 'text-gray-600 hover:bg-gray-100'
            )}>
              <LayoutDashboard className="w-4 h-4" />
              Dashboard
            </Link>
            <Link to="/upload" className={clsx(
              'flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
              isActive('/upload') ? 'bg-blue-50 text-blue-700' : 'text-gray-600 hover:bg-gray-100'
            )}>
              <Upload className="w-4 h-4" />
              Upload
            </Link>
          </div>

          {/* User menu */}
          <div className="relative">
            <button
              onClick={() => setDropdownOpen(!dropdownOpen)}
              className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-100 transition-colors"
            >
              <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                {user?.avatar_url
                  ? <img src={user.avatar_url} className="w-8 h-8 rounded-full" alt="" />
                  : <span className="text-blue-700 text-sm font-bold">
                      {user?.full_name?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase()}
                    </span>
                }
              </div>
              <div className="hidden sm:block text-left">
                <p className="text-sm font-medium text-gray-900">{user?.full_name || 'User'}</p>
                <p className="text-xs text-gray-500">{user?.email}</p>
              </div>
              <ChevronDown className="w-4 h-4 text-gray-500" />
            </button>

            {dropdownOpen && (
              <div className="absolute right-0 mt-1 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50">
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-2 w-full px-4 py-2 text-sm text-red-600 hover:bg-red-50"
                >
                  <LogOut className="w-4 h-4" />
                  Sign out
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  )
}
