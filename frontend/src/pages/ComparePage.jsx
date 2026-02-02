import { useState, useEffect } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { GitCompare, Loader2, AlertTriangle, CheckCircle, XCircle, FileText, List } from 'lucide-react'
import axios from 'axios'
import ClaimComparison from '../components/ClaimComparison'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function RiskIndicator({ level }) {
  const config = {
    high: { icon: XCircle, color: 'text-red-500', bg: 'bg-red-50', text: 'High Risk' },
    medium: { icon: AlertTriangle, color: 'text-yellow-500', bg: 'bg-yellow-50', text: 'Medium Risk' },
    low: { icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-50', text: 'Low Risk' },
  }
  
  const { icon: Icon, color, bg, text } = config[level] || config.low
  
  return (
    <div className={`flex items-center gap-2 px-4 py-2 rounded-lg ${bg}`}>
      <Icon className={color} size={24} />
      <span className={`font-semibold ${color}`}>{text}</span>
    </div>
  )
}

function TabButton({ active, onClick, icon: Icon, children }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-2 rounded-t-lg font-medium transition-colors ${
        active 
          ? 'bg-white text-blue-600 border-t border-l border-r' 
          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
      }`}
    >
      <Icon size={18} />
      {children}
    </button>
  )
}

export default function ComparePage() {
  const [sourceId, setSourceId] = useState('')
  const [targetId, setTargetId] = useState('')
  const [activeTab, setActiveTab] = useState('claims') // 'overview' or 'claims'
  
  // Get URL params
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const source = params.get('source')
    if (source) setSourceId(source)
  }, [])
  
  // Fetch patents list
  const patentsQuery = useQuery({
    queryKey: ['patents'],
    queryFn: async () => {
      const response = await axios.get(`${API_URL}/patents/?limit=100`)
      return response.data
    }
  })
  
  // Compare mutation (overview)
  const compareMutation = useMutation({
    mutationFn: async ({ source, target }) => {
      const response = await axios.post(`${API_URL}/patents/compare`, {
        source_patent_id: source,
        target_patent_id: target
      })
      return response.data
    }
  })
  
  const handleCompare = () => {
    if (sourceId && targetId) {
      compareMutation.mutate({ source: sourceId, target: targetId })
    }
  }
  
  const hasSelection = sourceId && targetId
  const hasResults = compareMutation.data
  
  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
          Compare Patents
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          Analyze potential infringement with AI-powered claim-level analysis
        </p>
      </div>
      
      {/* Selection */}
      <div className="card mb-8">
        <div className="grid md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Source Patent (Your Patent)
            </label>
            <select
              value={sourceId}
              onChange={(e) => setSourceId(e.target.value)}
              className="input"
            >
              <option value="">Select a patent...</option>
              {patentsQuery.data?.map(p => (
                <option key={p.id} value={p.id}>
                  {p.patent_number ? `[${p.patent_number}] ` : ''}{p.title.substring(0, 50)}...
                </option>
              ))}
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Target Patent (Potentially Infringing)
            </label>
            <select
              value={targetId}
              onChange={(e) => setTargetId(e.target.value)}
              className="input"
            >
              <option value="">Select a patent...</option>
              {patentsQuery.data?.map(p => (
                <option key={p.id} value={p.id}>
                  {p.patent_number ? `[${p.patent_number}] ` : ''}{p.title.substring(0, 50)}...
                </option>
              ))}
            </select>
          </div>
        </div>
        
        <button
          onClick={handleCompare}
          disabled={!sourceId || !targetId || compareMutation.isPending}
          className="btn-primary mt-6 flex items-center gap-2"
        >
          {compareMutation.isPending ? (
            <>
              <Loader2 className="animate-spin" size={18} />
              Analyzing...
            </>
          ) : (
            <>
              <GitCompare size={18} />
              Compare Patents
            </>
          )}
        </button>
      </div>
      
      {/* Results with Tabs */}
      {hasSelection && (
        <div>
          {/* Tabs */}
          <div className="flex gap-2 mb-0">
            <TabButton 
              active={activeTab === 'claims'} 
              onClick={() => setActiveTab('claims')}
              icon={List}
            >
              Claim Analysis
            </TabButton>
            <TabButton 
              active={activeTab === 'overview'} 
              onClick={() => setActiveTab('overview')}
              icon={FileText}
            >
              Overview
            </TabButton>
          </div>
          
          {/* Tab Content */}
          <div className="card rounded-tl-none">
            {activeTab === 'claims' ? (
              <ClaimComparison 
                sourcePatentId={sourceId} 
                targetPatentId={targetId} 
              />
            ) : (
              /* Overview Tab */
              hasResults ? (
                <div className="space-y-6">
                  {/* Risk Summary */}
                  <div className="flex items-center justify-between">
                    <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                      Overview Analysis
                    </h2>
                    <RiskIndicator level={compareMutation.data.risk_level} />
                  </div>
                  
                  {/* Scores */}
                  <div className="grid grid-cols-3 gap-4">
                    <div className="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                      <div className="text-2xl font-bold text-blue-600">
                        {(compareMutation.data.vector_similarity * 100).toFixed(1)}%
                      </div>
                      <div className="text-sm text-gray-500">Vector Similarity</div>
                    </div>
                    <div className="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                      <div className="text-2xl font-bold text-purple-600">
                        {(compareMutation.data.fuzzy_similarity * 100).toFixed(1)}%
                      </div>
                      <div className="text-sm text-gray-500">Fuzzy Similarity</div>
                    </div>
                    <div className="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                      <div className="text-2xl font-bold text-green-600">
                        {(compareMutation.data.confidence * 100).toFixed(1)}%
                      </div>
                      <div className="text-sm text-gray-500">Confidence</div>
                    </div>
                  </div>
                  
                  {/* Explanation */}
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-white mb-2">
                      AI Analysis
                    </h3>
                    <p className="text-gray-600 dark:text-gray-300">
                      {compareMutation.data.explanation}
                    </p>
                  </div>
                  
                  {/* Key Overlaps */}
                  {compareMutation.data.key_overlaps?.length > 0 && (
                    <div>
                      <h3 className="font-semibold text-gray-900 dark:text-white mb-2">
                        Key Overlaps
                      </h3>
                      <ul className="list-disc list-inside space-y-1 text-gray-600 dark:text-gray-300">
                        {compareMutation.data.key_overlaps.map((overlap, i) => (
                          <li key={i}>{overlap}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  
                  {/* Recommendation */}
                  <div className="p-4 bg-blue-50 dark:bg-blue-900/30 rounded-lg">
                    <h3 className="font-semibold text-blue-700 dark:text-blue-300 mb-1">
                      Recommendation
                    </h3>
                    <p className="text-blue-600 dark:text-blue-400">
                      {compareMutation.data.recommendation}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  Click "Compare Patents" to run overview analysis
                </div>
              )
            )}
          </div>
        </div>
      )}
    </div>
  )
}
