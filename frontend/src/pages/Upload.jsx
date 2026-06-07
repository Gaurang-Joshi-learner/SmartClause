import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../lib/api'
import { Upload as UploadIcon, FileText, X, CheckCircle, AlertCircle, Loader } from 'lucide-react'

export default function Upload() {
  const navigate = useNavigate()
  const inputRef = useRef()
  const [file, setFile] = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState('')

  const handleFile = (f) => {
    if (!f) return
    const ext = f.name.split('.').pop().toLowerCase()
    if (!['txt', 'pdf'].includes(ext)) {
      setError('Only .txt and .pdf files are supported')
      return
    }
    if (f.size > 10 * 1024 * 1024) {
      setError('File must be under 10MB')
      return
    }
    setError('')
    setFile(f)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    handleFile(e.dataTransfer.files[0])
  }

  const handleUpload = async () => {
    if (!file) return
    setUploading(true)
    setProgress(0)
    setError('')

    const form = new FormData()
    form.append('file', file)

    try {
      const { data } = await api.post('/contracts/upload', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: e => setProgress(Math.round((e.loaded / e.total) * 100)),
      })
      navigate(`/results/${data.id}`)
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed. Please try again.')
      setUploading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Upload Contract</h1>
        <p className="text-gray-500 mt-1">Upload a contract to extract ASC 606 revenue recognition clauses</p>
      </div>

      {/* Drop zone */}
      <div
        onDragOver={e => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => !file && inputRef.current?.click()}
        className={`card border-2 border-dashed transition-all cursor-pointer text-center py-12
          ${dragOver ? 'border-blue-400 bg-blue-50' : 'border-gray-300 hover:border-blue-400 hover:bg-blue-50/50'}
          ${file ? 'cursor-default' : ''}`}
      >
        <input ref={inputRef} type="file" accept=".txt,.pdf" className="hidden"
          onChange={e => handleFile(e.target.files[0])} />

        {!file ? (
          <>
            <div className="w-16 h-16 bg-blue-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <UploadIcon className="w-8 h-8 text-blue-600" />
            </div>
            <p className="text-lg font-medium text-gray-700">Drop your contract here</p>
            <p className="text-gray-400 text-sm mt-1">or click to browse</p>
            <p className="text-xs text-gray-400 mt-3">Supports PDF and TXT · Max 10MB</p>
          </>
        ) : (
          <div className="flex items-center gap-4 justify-center">
            <div className="w-12 h-12 bg-blue-50 rounded-xl flex items-center justify-center">
              <FileText className="w-6 h-6 text-blue-600" />
            </div>
            <div className="text-left">
              <p className="font-medium text-gray-900">{file.name}</p>
              <p className="text-sm text-gray-400">{(file.size / 1024).toFixed(1)} KB</p>
            </div>
            <button onClick={e => { e.stopPropagation(); setFile(null) }}
              className="ml-4 p-1.5 hover:bg-gray-100 rounded-lg text-gray-400">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />{error}
        </div>
      )}

      {/* Upload progress */}
      {uploading && (
        <div className="mt-4">
          <div className="flex items-center justify-between text-sm text-gray-600 mb-1">
            <span>Uploading...</span><span>{progress}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div className="bg-blue-600 h-2 rounded-full transition-all duration-300" style={{ width: `${progress}%` }} />
          </div>
          {progress === 100 && (
            <p className="text-sm text-blue-600 mt-2 flex items-center gap-1">
              <Loader className="w-3.5 h-3.5 animate-spin" />
              Running ASC 606 extraction pipeline...
            </p>
          )}
        </div>
      )}

      {/* What happens next */}
      <div className="card mt-6 bg-blue-50 border-blue-100">
        <h3 className="font-medium text-blue-900 mb-3">What happens after upload</h3>
        <div className="space-y-2">
          {[
            'Contract text is extracted and split into sections',
            'All 10 ASC 606 clause types are identified and classified',
            'Values, dates, and amounts are parsed from each clause',
            'Accounting risk flags are generated per clause',
            'Full structured JSON is stored and available for download',
          ].map((step, i) => (
            <div key={i} className="flex items-start gap-2 text-sm text-blue-800">
              <CheckCircle className="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" />
              {step}
            </div>
          ))}
        </div>
      </div>

      <button onClick={handleUpload} disabled={!file || uploading}
        className="btn-primary w-full mt-6 py-3 flex items-center justify-center gap-2 text-base">
        {uploading
          ? <><Loader className="w-5 h-5 animate-spin" />Processing...</>
          : <><UploadIcon className="w-5 h-5" />Extract Clauses</>}
      </button>
    </div>
  )
}
