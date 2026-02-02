import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { 
  Search, Download, Loader2, Check, X, Building2, 
  FileText, Calendar, Tag, ChevronDown, ChevronUp,
  AlertCircle, CheckCircle
} from 'lucide-react'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Common CPC codes for quick access
const CPC_CODES = [
  { code: 'G06F', label: 'Computing/Calculating' },
  { code: 'G06N', label: 'AI/ML/Neural Networks' },
  { code: 'G06Q', label: 'Business Methods' },
  { code: 'H04L', label: 'Network Protocols' },
  { code: 'H04W', label: 'Wireless Communication' },
  { code: 'G06K', label: 'Data Recognition' },
  { code: 'G06V', label: 'Image/Video Analysis' },
  { code: 'G16H', label: 'Healthcare Informatics' },
]

function PatentPreview({ patent, selected, onToggle, onViewDetails }) {
  return (
    <div 
      className={`p-4 rounded-lg border-2 transition-all cursor-pointer ${
        patent.already_imported 
          ? 'border-gray-200 bg-gray-50 opacity-60' 
          : selected 
            ? 'border-blue-500 bg-blue-50' 
            : 'border-gray-200 hover:border-gray-300'
      }`}
      onClick={() => !patent.already_imported && onToggle(patent.patent_number)}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-mono text-gray-500">
              #{patent.patent_number}
            </span>
            {patent.already_imported && (
              <span className="text-xs px-2 py-0.5 bg-green-100 text-green-700 rounded">
                Already imported
              </span>
            )}
            {patent.classification && (
              <span className="text-xs px-2 py-0.5 bg-purple-100 text-purple-700 rounded">
                {patent.classification}
              </span>
            )}
          </div>
          <h3 className="font-medium text-gray-900 mb-1 line-clamp-2">
            {patent.title}
          </h3>
          <p className="text-sm text-gray-600 line-clamp-2">
            {patent.abstract}
          </p>
          <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
            {patent.applicant && (
              <span className="flex items-center gap-1">
                <Building2 size={12} />
                {patent.applicant}
              </span>
            )}
            {patent.publication_date && (
              <span className="flex items-center gap-1">
                <Calendar size={12} />
                {patent.publication_date}
              </span>
            )}
          </div>
        </div>
        
        <div className="ml-4 flex flex-col items-center gap-2">
          {!patent.already_imported && (
            <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center ${
              selected ? 'border-blue-500 bg-blue-500' : 'border-gray-300'
            }`}>
              {selected && <Check size={14} className="text-white" />}
            </div>
          )}
          <button
            onClick={(e) => {
              e.stopPropagation()
              onViewDetails(patent.patent_number)
            }}
            className="text-xs text-blue-600 hover:underline"
          >
            Details
          </button>
        </div>
      </div>
    </div>
  )
}

function ImportResults({ results }) {
  const successful = results.filter(r => r.success)
  const failed = results.filter(r => !r.success)
  
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-green-600">
          <CheckCircle size={20} />
          <span className="font-medium">{successful.length} imported</span>
        </div>
        {failed.length > 0 && (
          <div className="flex items-center gap-2 text-red-600">
            <AlertCircle size={20} />
            <span className="font-medium">{failed.length} failed</span>
          </div>
        )}
      </div>
      
      {failed.length > 0 && (
        <div className="p-3 bg-red-50 rounded-lg">
          <p className="text-sm font-medium text-red-700 mb-2">Failed imports:</p>
          <ul className="text-sm text-red-600 space-y-1">
            {failed.map((r, i) => (
              <li key={i}>#{r.patent_number}: {r.error}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

export default function ImportPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [cpcCode, setCpcCode] = useState('')
  const [assignee, setAssignee] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [selectedPatents, setSelectedPatents] = useState(new Set())
  const [showAdvanced, setShowAdvanced] = useState(false)
  
  // Search USPTO
  const searchMutation = useMutation({
    mutationFn: async () => {
      const response = await axios.post(`${API_URL}/ingest/uspto/search`, {
        query: searchQuery,
        cpc_code: cpcCode || undefined,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
        limit: 50
      })
      return response.data
    },
    onSuccess: () => {
      setSelectedPatents(new Set())
    }
  })
  
  // Import selected patents
  const importMutation = useMutation({
    mutationFn: async (patentNumbers) => {
      const response = await axios.post(`${API_URL}/ingest/uspto/import`, {
        patent_numbers: patentNumbers
      })
      return response.data
    },
    onSuccess: () => {
      setSelectedPatents(new Set())
      // Refresh search results
      if (searchQuery || cpcCode) {
        searchMutation.mutate()
      }
    }
  })
  
  // View patent details
  const detailsMutation = useMutation({
    mutationFn: async (patentNumber) => {
      const response = await axios.get(`${API_URL}/ingest/uspto/patent/${patentNumber}`)
      return response.data
    }
  })
  
  const handleSearch = (e) => {
    e.preventDefault()
    if (searchQuery || cpcCode || assignee) {
      searchMutation.mutate()
    }
  }
  
  const togglePatent = (patentNumber) => {
    const newSelected = new Set(selectedPatents)
    if (newSelected.has(patentNumber)) {
      newSelected.delete(patentNumber)
    } else {
      newSelected.add(patentNumber)
    }
    setSelectedPatents(newSelected)
  }
  
  const selectAll = () => {
    if (!searchMutation.data) return
    const available = searchMutation.data.patents
      .filter(p => !p.already_imported)
      .map(p => p.patent_number)
    setSelectedPatents(new Set(available))
  }
  
  const handleImport = () => {
    if (selectedPatents.size > 0) {
      importMutation.mutate(Array.from(selectedPatents))
    }
  }
  
  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
          Import from USPTO
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          Search and import real patents from the US Patent Office database
        </p>
      </div>
      
      {/* Search Form */}
      <div className="card mb-8">
        <form onSubmit={handleSearch}>
          {/* Main search */}
          <div className="flex gap-4 mb-4">
            <div className="flex-1">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by keywords (e.g., machine learning, neural network)"
                className="input"
              />
            </div>
            <button
              type="submit"
              disabled={searchMutation.isPending || (!searchQuery && !cpcCode)}
              className="btn-primary flex items-center gap-2"
            >
              {searchMutation.isPending ? (
                <Loader2 className="animate-spin" size={18} />
              ) : (
                <Search size={18} />
              )}
              Search USPTO
            </button>
          </div>
          
          {/* Quick CPC filters */}
          <div className="mb-4">
            <label className="text-sm text-gray-600 dark:text-gray-400 mb-2 block">
              Quick filters by technology:
            </label>
            <div className="flex flex-wrap gap-2">
              {CPC_CODES.map(({ code, label }) => (
                <button
                  key={code}
                  type="button"
                  onClick={() => setCpcCode(cpcCode === code ? '' : code)}
                  className={`px-3 py-1.5 rounded-full text-sm transition-colors ${
                    cpcCode === code
                      ? 'bg-purple-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  <span className="font-mono mr-1">{code}</span>
                  <span className="text-xs opacity-75">{label}</span>
                </button>
              ))}
            </div>
          </div>
          
          {/* Advanced options */}
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900"
          >
            {showAdvanced ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            Advanced filters
          </button>
          
          {showAdvanced && (
            <div className="grid md:grid-cols-3 gap-4 mt-4 pt-4 border-t">
              <div>
                <label className="text-sm text-gray-600 mb-1 block">Assignee/Company</label>
                <input
                  type="text"
                  value={assignee}
                  onChange={(e) => setAssignee(e.target.value)}
                  placeholder="e.g., Google, Apple"
                  className="input"
                />
              </div>
              <div>
                <label className="text-sm text-gray-600 mb-1 block">Start Date</label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="input"
                />
              </div>
              <div>
                <label className="text-sm text-gray-600 mb-1 block">End Date</label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="input"
                />
              </div>
            </div>
          )}
        </form>
      </div>
      
      {/* Import Results */}
      {importMutation.data && (
        <div className="card mb-6">
          <ImportResults results={importMutation.data.results} />
        </div>
      )}
      
      {/* Search Error */}
      {searchMutation.isError && (
        <div className="flex items-center gap-2 p-4 bg-red-50 text-red-700 rounded-lg mb-6">
          <AlertCircle size={20} />
          <span>Search failed: {searchMutation.error?.message}</span>
        </div>
      )}
      
      {/* Search Results */}
      {searchMutation.data && (
        <div>
          {/* Results header */}
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                Results ({searchMutation.data.total})
              </h2>
              <p className="text-sm text-gray-500">
                {selectedPatents.size} selected for import
              </p>
            </div>
            
            <div className="flex items-center gap-3">
              <button
                onClick={selectAll}
                className="text-sm text-blue-600 hover:underline"
              >
                Select all available
              </button>
              <button
                onClick={handleImport}
                disabled={selectedPatents.size === 0 || importMutation.isPending}
                className="btn-primary flex items-center gap-2"
              >
                {importMutation.isPending ? (
                  <>
                    <Loader2 className="animate-spin" size={18} />
                    Importing...
                  </>
                ) : (
                  <>
                    <Download size={18} />
                    Import Selected ({selectedPatents.size})
                  </>
                )}
              </button>
            </div>
          </div>
          
          {/* Patent list */}
          <div className="space-y-3">
            {searchMutation.data.patents.map((patent) => (
              <PatentPreview
                key={patent.patent_number}
                patent={patent}
                selected={selectedPatents.has(patent.patent_number)}
                onToggle={togglePatent}
                onViewDetails={(num) => detailsMutation.mutate(num)}
              />
            ))}
          </div>
          
          {searchMutation.data.patents.length === 0 && (
            <div className="text-center py-12 text-gray-500">
              No patents found matching your search
            </div>
          )}
        </div>
      )}
      
      {/* Patent Details Modal */}
      {detailsMutation.data && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl max-w-3xl w-full max-h-[80vh] overflow-hidden">
            <div className="p-6 border-b flex items-center justify-between">
              <div>
                <span className="text-sm font-mono text-gray-500">
                  #{detailsMutation.data.patent_number}
                </span>
                <h3 className="text-lg font-semibold">{detailsMutation.data.title}</h3>
              </div>
              <button
                onClick={() => detailsMutation.reset()}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                <X size={20} />
              </button>
            </div>
            <div className="p-6 overflow-y-auto max-h-[60vh]">
              <div className="space-y-4">
                <div>
                  <h4 className="font-medium text-gray-700 mb-1">Abstract</h4>
                  <p className="text-sm text-gray-600">{detailsMutation.data.abstract}</p>
                </div>
                
                {detailsMutation.data.claims && (
                  <div>
                    <h4 className="font-medium text-gray-700 mb-1">Claims</h4>
                    <pre className="text-sm text-gray-600 whitespace-pre-wrap bg-gray-50 p-3 rounded-lg max-h-64 overflow-y-auto">
                      {detailsMutation.data.claims}
                    </pre>
                  </div>
                )}
                
                <div className="grid grid-cols-2 gap-4 text-sm">
                  {detailsMutation.data.applicant && (
                    <div>
                      <span className="text-gray-500">Assignee:</span>{' '}
                      <span className="font-medium">{detailsMutation.data.applicant}</span>
                    </div>
                  )}
                  {detailsMutation.data.inventors && (
                    <div>
                      <span className="text-gray-500">Inventors:</span>{' '}
                      <span className="font-medium">{detailsMutation.data.inventors}</span>
                    </div>
                  )}
                  {detailsMutation.data.publication_date && (
                    <div>
                      <span className="text-gray-500">Published:</span>{' '}
                      <span className="font-medium">{detailsMutation.data.publication_date}</span>
                    </div>
                  )}
                  {detailsMutation.data.classification && (
                    <div>
                      <span className="text-gray-500">Classification:</span>{' '}
                      <span className="font-medium font-mono">{detailsMutation.data.classification}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
