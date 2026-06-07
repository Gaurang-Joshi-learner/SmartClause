import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../lib/api'
import { useAuth } from '../context/AuthContext'
import { Upload, FileText, Clock, CheckCircle, XCircle, Loader, Trash2, Eye, TrendingUp } from 'lucide-react'
import { formatDistanceToNow } from '../lib/utils'

const STATUS_CONFIG = {
  done:       { icon: CheckCircle, color: 'text-green-600', bg: 'bg-green-50', label: 'Done' },
  processing: { icon: Loader,       color: 'text-blue-600',  bg: 'bg-blue-50',  label: 'Processing' },
  uploaded:   { icon: Clock,        color: 'text-yellow-600',bg: 'bg-yellow-50',label: 'Queued' },
  failed:     { icon: XCircle,      color: 'text-red-600',   bg: 'bg-red-50',   label: 'Failed' },
}

export default function Dashboard() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [contracts, setContracts] = useState([])
  const [loading, setLoading] = useState(true)
  const [deleting, setDeleting] = useState(null)

  const fetchContracts = async () => {
    try {
      const { data } = await api.get('/contracts/')
      setContracts(data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchContracts()
    // Poll every 5s if any contract is processing
    const interval = setInterval(() => {
      if (contracts.some(c => c.status === 'processing' || c.status === 'uploaded')) {
        fetchContracts()
      }
    }, 5000)
    return () => clearInterval(interval)
  }, [contracts.length])

  const handleDelete = async (id, e) => {
    e.stopPropagation()
    if (!confirm('Delete this contract and all its extracted data?')) return
    setDeleting(id)
    try {
      await api.delete(`/contracts/${id}`)
      setContracts(prev => prev.filter(c => c.id !== id))
    } finally {
      setDeleting(null)
    }
  }

  const doneContracts = contracts.filter(c => c.status === 'done').length
  const totalContracts = contracts.length

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Welcome back, {user?.full_name?.split(' ')[0] || 'there'} 👋
          </h1>
          <p className="text-gray-500 mt-1">Manage your ASC 606 contract analyses</p>
        </div>
        <Link to="/upload" className="btn-primary flex items-center gap-2">
          <Upload className="w-4 h-4" />
          Upload Contract
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        {[
          { label: 'Total Contracts', value: totalContracts, icon: FileText, color: 'blue' },
          { label: 'Analysed', value: doneContracts, icon: CheckCircle, color: 'green' },
          { label: 'Processing', value: contracts.filter(c=>c.status==='processing').length, icon: Loader, color: 'yellow' },
        ].map(stat => (
          <div key={stat.label} className="card flex items-center gap-4">
            <div className={`w-12 h-12 rounded-xl bg-${stat.color}-50 flex items-center justify-center flex-shrink-0`}>
              <stat.icon className={`w-6 h-6 text-${stat.color}-600`} />
            </div>
            <div>
              <p className="text-4xl font-bold text-gray-900">{stat.value}</p>
              <p className="text-sm text-gray-500">{stat.label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Contracts table */}
      <div className="card p-0 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="font-semibold text-gray-900">All Contracts</h2>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader className="w-8 h-8 text-blue-600 animate-spin" />
          </div>
        ) : contracts.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <FileText className="w-12 h-12 text-gray-300 mb-3" />
            <p className="text-gray-500 font-medium">No contracts yet</p>
            <p className="text-gray-400 text-sm mb-4">Upload your first contract to get started</p>
            <Link to="/upload" className="btn-primary flex items-center gap-2">
              <Upload className="w-4 h-4" />Upload Contract
            </Link>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {contracts.map(contract => {
              const cfg = STATUS_CONFIG[contract.status] || STATUS_CONFIG.uploaded
              const Icon = cfg.icon
              return (
                <div key={contract.id}
                  onClick={() => contract.status === 'done' && navigate(`/results/${contract.id}`)}
                  className={`flex items-center gap-4 px-6 py-4 hover:bg-gray-50 transition-colors ${contract.status === 'done' ? 'cursor-pointer' : ''}`}
                >
                  <div className="w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center flex-shrink-0">
                    <FileText className="w-5 h-5 text-blue-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900 truncate">{contract.filename}</p>
                    <p className="text-sm text-gray-500">
                      {formatDistanceToNow(contract.created_at)} · {(contract.file_size_bytes / 1024).toFixed(1)} KB
                    </p>
                  </div>
                  <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium ${cfg.bg} ${cfg.color}`}>
                    <Icon className={`w-3.5 h-3.5 ${contract.status === 'processing' ? 'animate-spin' : ''}`} />
                    {cfg.label}
                  </div>
                  <div className="flex items-center gap-2">
                    {contract.status === 'done' && (
                      <button onClick={e => { e.stopPropagation(); navigate(`/results/${contract.id}`) }}
                        className="p-2 hover:bg-blue-50 rounded-lg text-blue-600 transition-colors">
                        <Eye className="w-4 h-4" />
                      </button>
                    )}
                    <button onClick={e => handleDelete(contract.id, e)} disabled={deleting === contract.id}
                      className="p-2 hover:bg-red-50 rounded-lg text-red-400 hover:text-red-600 transition-colors">
                      {deleting === contract.id
                        ? <Loader className="w-4 h-4 animate-spin" />
                        : <Trash2 className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
