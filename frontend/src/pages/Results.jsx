import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../lib/api'
import { ArrowLeft, Download, Loader, AlertCircle, ChevronDown, ChevronUp,
         DollarSign, Clock, FileText, AlertTriangle, CheckCircle, RefreshCw } from 'lucide-react'
import clsx from 'clsx'

const STEP_LABELS = {
  2: { label: 'Step 2: Performance Obligations', color: 'blue' },
  3: { label: 'Step 3: Transaction Price',        color: 'green' },
  5: { label: 'Step 5: Revenue Recognition',      color: 'purple' },
  null: { label: 'Supporting Clauses',            color: 'gray' },
}

const CONFIDENCE_CONFIG = {
  high:   { label: 'High',   color: 'text-green-700', bg: 'bg-green-100' },
  medium: { label: 'Medium', color: 'text-yellow-700', bg: 'bg-yellow-100' },
  low:    { label: 'Low',    color: 'text-red-700',   bg: 'bg-red-100' },
}

function getConf(c) {
  if (c >= 0.85) return 'high'
  if (c >= 0.70) return 'medium'
  return 'low'
}

function MetricCard({ label, value, icon: Icon, color = 'blue' }) {
  return (
    <div className="card">
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm text-gray-500">{label}</p>
        <div className={`w-8 h-8 bg-${color}-50 rounded-lg flex items-center justify-center`}>
          <Icon className={`w-4 h-4 text-${color}-600`} />
        </div>
      </div>
      <p className="text-xl font-bold text-gray-900">{value}</p>
    </div>
  )
}

function ClauseCard({ clause }) {
  const [open, setOpen] = useState(false)
  const conf = getConf(clause.confidence)
  const cfg = CONFIDENCE_CONFIG[conf]

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <button onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-4 py-3 bg-white hover:bg-gray-50 transition-colors text-left">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-bold text-gray-500 uppercase tracking-wide">{clause.clause_type.replace(/_/g,' ')}</span>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${cfg.bg} ${cfg.color}`}>
              {(clause.confidence * 100).toFixed(0)}% {cfg.label}
            </span>
          </div>
          <p className="text-sm text-gray-600 truncate mt-0.5">{clause.section}</p>
        </div>
        {open ? <ChevronUp className="w-4 h-4 text-gray-400 flex-shrink-0" />
               : <ChevronDown className="w-4 h-4 text-gray-400 flex-shrink-0" />}
      </button>

      {open && (
        <div className="px-4 py-4 border-t border-gray-100 bg-gray-50 space-y-4">
          {clause.asc606_relevance && (
            <div className="p-3 bg-blue-50 rounded-lg">
              <p className="text-xs font-semibold text-blue-700 uppercase tracking-wide mb-1">ASC 606 Relevance</p>
              <p className="text-sm text-blue-800">{clause.asc606_relevance}</p>
            </div>
          )}
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Extracted Text</p>
            <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed bg-white border border-gray-200 rounded p-3 max-h-40 overflow-y-auto">
              {clause.extracted_text}
            </p>
          </div>
          {Object.keys(clause.extracted_values || {}).length > 0 && (
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Extracted Values</p>
              <pre className="text-xs bg-gray-900 text-green-400 rounded p-3 overflow-x-auto">
                {JSON.stringify(clause.extracted_values, null, 2)}
              </pre>
            </div>
          )}
          {clause.flags?.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Accounting Flags</p>
              <div className="space-y-1.5">
                {clause.flags.map((flag, i) => (
                  <div key={i} className="flex items-start gap-2 p-2 bg-amber-50 border border-amber-200 rounded text-xs text-amber-800">
                    <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />{flag}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function Results() {
  const { contractId } = useParams()
  const navigate = useNavigate()
  const [contract, setContract] = useState(null)
  const [summary, setSummary] = useState(null)
  const [clauses, setClauses] = useState([])
  const [loading, setLoading] = useState(true)
  const [polling, setPolling] = useState(false)
  const [error, setError] = useState('')

  const fetchData = async () => {
    try {
      const [contractRes, summaryRes, clausesRes] = await Promise.all([
        api.get(`/contracts/${contractId}`),
        api.get(`/extractions/${contractId}/summary`).catch(() => null),
        api.get(`/extractions/${contractId}/clauses`).catch(() => ({ data: [] })),
      ])
      setContract(contractRes.data)
      if (summaryRes) setSummary(summaryRes.data)
      setClauses(clausesRes.data)
    } catch (e) {
      setError('Failed to load results')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [contractId])

  // Poll while processing
  useEffect(() => {
    if (!contract) return
    if (contract.status === 'processing' || contract.status === 'uploaded') {
      setPolling(true)
      const t = setInterval(fetchData, 3000)
      return () => clearInterval(t)
    } else {
      setPolling(false)
    }
  }, [contract?.status])

  const downloadJson = () => {
    const blob = new Blob([JSON.stringify({ contract, summary, clauses }, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${contract?.filename || 'contract'}_asc606.json`
    a.click()
  }

  // Group clauses by step
  const grouped = clauses.reduce((acc, c) => {
    const step = c.asc606_step ?? null
    acc[step] = acc[step] || []
    acc[step].push(c)
    return acc
  }, {})

  if (loading) return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <Loader className="w-8 h-8 text-blue-600 animate-spin" />
    </div>
  )

  if (error) return (
    <div className="max-w-2xl mx-auto px-4 py-12 text-center">
      <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-3" />
      <p className="text-gray-700">{error}</p>
      <button onClick={() => navigate('/dashboard')} className="btn-secondary mt-4">Back to Dashboard</button>
    </div>
  )

  // Still processing
  if (contract?.status !== 'done') return (
    <div className="max-w-2xl mx-auto px-4 py-12 text-center">
      <div className="w-16 h-16 bg-blue-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
        <Loader className="w-8 h-8 text-blue-600 animate-spin" />
      </div>
      <h2 className="text-xl font-bold text-gray-900 mb-2">
        {contract?.status === 'failed' ? 'Extraction Failed' : 'Processing Contract...'}
      </h2>
      <p className="text-gray-500">
        {contract?.status === 'failed'
          ? contract.error_message || 'An error occurred during extraction'
          : 'Running ASC 606 extraction pipeline. This usually takes 5–15 seconds.'}
      </p>
      {polling && <p className="text-xs text-blue-500 mt-3 flex items-center justify-center gap-1"><RefreshCw className="w-3 h-3 animate-spin" />Auto-refreshing...</p>}
      <button onClick={() => navigate('/dashboard')} className="btn-secondary mt-6">Back to Dashboard</button>
    </div>
  )
const exportPdf = async () => {
  try {
    const response = await api.get(
      `/contracts/${contractId}/export-pdf`,
      {
        responseType: 'blob',
      }
    )

    const url = window.URL.createObjectURL(
      new Blob([response.data])
    )

    const link = document.createElement('a')
    link.href = url
    link.download = `${contract.filename}_report.pdf`
    document.body.appendChild(link)
    link.click()
    link.remove()

    window.URL.revokeObjectURL(url)
  } catch (err) {
    console.error('PDF export failed', err)
    alert('Failed to export PDF')
  }
}
  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/dashboard')} className="p-2 hover:bg-gray-100 rounded-lg text-gray-500">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-xl font-bold text-gray-900">{contract?.filename}</h1>
            <p className="text-sm text-gray-500">{clauses.length} clauses extracted</p>
          </div>
        </div>
        <button
  onClick={exportPdf}
  className="btn-primary flex items-center gap-2"
>
  <Download className="w-4 h-4" />
  Export PDF
</button>
        
      </div>

      {/* Summary metrics */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
          <MetricCard label="Contract Value" icon={DollarSign} color="green"
            value={summary.total_contract_value_usd > 0
              ? `$${(summary.total_contract_value_usd).toLocaleString()}`
              : 'N/A'} />
          <MetricCard label="Duration" icon={Clock} color="blue"
            value={summary.duration_months ? `${summary.duration_months} months` : 'N/A'} />
          <MetricCard label="Total Clauses" icon={FileText} color="indigo"
            value={summary.total_clauses} />
          <MetricCard label="Avg Confidence" icon={CheckCircle} color="purple"
            value={`${(summary.average_confidence * 100).toFixed(0)}%`} />
        </div>
      )}

      {/* Recognition info */}
      {summary?.license_type && (
        <div className="card mb-6 bg-indigo-50 border-indigo-100">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
            <div><p className="text-xs text-indigo-500 uppercase font-semibold">License Type</p>
              <p className="font-bold text-indigo-900 mt-1">{summary.license_type}</p></div>
            <div><p className="text-xs text-indigo-500 uppercase font-semibold">Recognition</p>
              <p className="font-bold text-indigo-900 mt-1">{summary.recognition_pattern}</p></div>
            <div><p className="text-xs text-indigo-500 uppercase font-semibold">Variable Consideration</p>
              <p className="font-bold text-indigo-900 mt-1">{summary.has_variable_consideration ? 'Yes' : 'No'}</p></div>
            <div><p className="text-xs text-indigo-500 uppercase font-semibold">Refund Rights</p>
              <p className="font-bold text-indigo-900 mt-1">{summary.has_refund_rights ? 'Yes' : 'No'}</p></div>
          </div>
        </div>
      )}

      {/* Risk flags */}
      {summary?.risk_flags?.length > 0 && (
        <div className="card mb-6">
          <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-500" />
            ASC 606 Risk Flags ({summary.risk_flags.length})
          </h3>
          <div className="space-y-1.5 max-h-48 overflow-y-auto">
            {summary.risk_flags.map((flag, i) => (
              <div key={i} className="text-xs p-2 bg-amber-50 border border-amber-200 rounded text-amber-800">
                {flag}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Clauses by step */}
      <div className="space-y-6">
        {[2, 3, 5, null].map(step => {
          const stepClauses = grouped[step]
          if (!stepClauses?.length) return null
          const cfg = STEP_LABELS[step]
          return (
            <div key={step ?? 'null'}>
              <h2 className={`text-sm font-bold text-${cfg.color}-700 uppercase tracking-wide mb-3 flex items-center gap-2`}>
                <div className={`w-2 h-2 bg-${cfg.color}-500 rounded-full`} />
                {cfg.label}
                <span className={`text-xs font-normal text-${cfg.color}-500`}>({stepClauses.length})</span>
              </h2>
              <div className="space-y-2">
                {stepClauses.map(c => <ClauseCard key={c.id} clause={c} />)}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
