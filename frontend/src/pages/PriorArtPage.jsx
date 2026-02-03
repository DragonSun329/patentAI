import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { 
  Search, Loader2, AlertTriangle, CheckCircle, XCircle, 
  ChevronDown, ChevronUp, Lightbulb, Shield, FileWarning,
  ArrowRight, Sparkles
} from 'lucide-react'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function RiskBadge({ level, size = 'md' }) {
  const config = {
    high: { color: 'bg-red-100 text-red-700', icon: XCircle },
    medium: { color: 'bg-yellow-100 text-yellow-700', icon: AlertTriangle },
    low: { color: 'bg-green-100 text-green-700', icon: CheckCircle },
  }
  const { color, icon: Icon } = config[level] || config.low
  const sizeClass = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm'
  
  return (
    <span className={`inline-flex items-center gap-1 rounded-full font-medium ${color} ${sizeClass}`}>
      <Icon size={size === 'sm' ? 12 : 14} />
      {level.charAt(0).toUpperCase() + level.slice(1)}
    </span>
  )
}

function FreedomIndicator({ status }) {
  const config = {
    likely: { 
      color: 'bg-green-50 border-green-200', 
      textColor: 'text-green-700',
      icon: CheckCircle,
      label: 'Freedom to Operate: Likely'
    },
    uncertain: { 
      color: 'bg-yellow-50 border-yellow-200', 
      textColor: 'text-yellow-700',
      icon: AlertTriangle,
      label: 'Freedom to Operate: Uncertain'
    },
    unlikely: { 
      color: 'bg-red-50 border-red-200', 
      textColor: 'text-red-700',
      icon: XCircle,
      label: 'Freedom to Operate: Unlikely'
    },
  }
  const { color, textColor, icon: Icon, label } = config[status] || config.uncertain
  
  return (
    <div className={`p-4 rounded-lg border ${color} flex items-center gap-3`}>
      <Icon className={textColor} size={24} />
      <span className={`font-semibold ${textColor}`}>{label}</span>
    </div>
  )
}

function BlockingClaimCard({ claim }) {
  const [expanded, setExpanded] = useState(false)
  
  return (
    <div className="p-3 bg-gray-50 rounded-lg">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-medium">
              Claim {claim.claim_number}
            </span>
            {claim.is_independent && (
              <span className="text-xs px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded">
                Independent
              </span>
            )}
            <RiskBadge level={claim.risk_level} size="sm" />
            <span className="text-xs text-gray-500">
              {(claim.similarity * 100).toFixed(0)}% match
            </span>
          </div>
          <p className={`text-sm text-gray-600 ${expanded ? '' : 'line-clamp-2'}`}>
            {claim.claim_text}
          </p>
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="ml-2 p-1 hover:bg-gray-200 rounded"
        >
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
      </div>
    </div>
  )
}

function BlockingPatentCard({ patent }) {
  const [expanded, setExpanded] = useState(false)
  
  return (
    <div className="border rounded-xl overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-4 flex items-start justify-between bg-white hover:bg-gray-50 transition-colors text-left"
      >
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            {patent.patent_number && (
              <span className="text-sm font-mono text-gray-500">
                #{patent.patent_number}
              </span>
            )}
            <RiskBadge level={patent.overall_risk} />
          </div>
          <h3 className="font-semibold text-gray-900">{patent.title}</h3>
          <div className="flex items-center gap-4 mt-1 text-xs text-gray-500">
            {patent.applicant && <span>{patent.applicant}</span>}
            <span>{patent.blocking_claims.length} blocking claim(s)</span>
            <span>Top match: {(patent.highest_similarity * 100).toFixed(0)}%</span>
          </div>
        </div>
        {expanded ? <ChevronUp /> : <ChevronDown />}
      </button>
      
      {/* Expanded content */}
      {expanded && (
        <div className="p-4 border-t bg-gray-50/50">
          <div className="mb-4">
            <h4 className="text-sm font-medium text-gray-700 mb-1">Abstract</h4>
            <p className="text-sm text-gray-600">{patent.abstract}</p>
          </div>
          
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-2">
              Potentially Blocking Claims
            </h4>
            <div className="space-y-2">
              {patent.blocking_claims.map((claim, i) => (
                <BlockingClaimCard key={i} claim={claim} />
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function AnalysisPanel({ analysis }) {
  if (!analysis) return null
  
  return (
    <div className="card space-y-4">
      <div className="flex items-center gap-2">
        <Sparkles className="text-purple-500" size={20} />
        <h3 className="font-semibold text-gray-900">AI Analysis</h3>
      </div>
      
      <FreedomIndicator status={analysis.freedom_to_operate} />
      
      {analysis.key_risks?.length > 0 && (
        <div>
          <h4 className="flex items-center gap-2 text-sm font-medium text-red-700 mb-2">
            <FileWarning size={16} />
            Key Risks
          </h4>
          <ul className="space-y-1">
            {analysis.key_risks.map((risk, i) => (
              <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                <span className="text-red-400 mt-1">•</span>
                {risk}
              </li>
            ))}
          </ul>
        </div>
      )}
      
      {analysis.design_around_suggestions?.length > 0 && (
        <div>
          <h4 className="flex items-center gap-2 text-sm font-medium text-green-700 mb-2">
            <Lightbulb size={16} />
            Design-Around Suggestions
          </h4>
          <ul className="space-y-1">
            {analysis.design_around_suggestions.map((suggestion, i) => (
              <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                <span className="text-green-400 mt-1">•</span>
                {suggestion}
              </li>
            ))}
          </ul>
        </div>
      )}
      
      {analysis.recommendation && (
        <div className="p-3 bg-blue-50 rounded-lg">
          <h4 className="flex items-center gap-2 text-sm font-medium text-blue-700 mb-1">
            <ArrowRight size={16} />
            Recommendation
          </h4>
          <p className="text-sm text-blue-600">{analysis.recommendation}</p>
        </div>
      )}
    </div>
  )
}

export default function PriorArtPage() {
  const [invention, setInvention] = useState('')
  
  const searchMutation = useMutation({
    mutationFn: async () => {
      const response = await axios.post(`${API_URL}/priorart/search`, {
        invention_description: invention,
        limit: 20,
        include_analysis: true
      })
      return response.data
    }
  })
  
  const handleSearch = (e) => {
    e.preventDefault()
    if (invention.length >= 50) {
      searchMutation.mutate()
    }
  }
  
  const data = searchMutation.data
  
  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
          Prior Art Search
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          Describe your invention to find patents that might block it
        </p>
      </div>
      
      {/* Search Form */}
      <div className="card mb-8">
        <form onSubmit={handleSearch}>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Describe Your Invention
          </label>
          <textarea
            value={invention}
            onChange={(e) => setInvention(e.target.value)}
            placeholder="Describe your invention in detail. Include the technical approach, key components, and how it works. The more detail you provide, the better the prior art search will be.

Example: A machine learning system that uses transformer architecture to analyze patent claims and identify potential infringement. The system generates embeddings for each claim independently and uses cosine similarity to find matching claims across a patent database..."
            className="input min-h-[200px] resize-y"
            rows={8}
          />
          
          <div className="flex items-center justify-between mt-4">
            <span className="text-sm text-gray-500">
              {invention.length} characters
              {invention.length < 50 && invention.length > 0 && (
                <span className="text-red-500"> (minimum 50)</span>
              )}
            </span>
            
            <button
              type="submit"
              disabled={invention.length < 50 || searchMutation.isPending}
              className="btn-primary flex items-center gap-2"
            >
              {searchMutation.isPending ? (
                <>
                  <Loader2 className="animate-spin" size={18} />
                  Searching...
                </>
              ) : (
                <>
                  <Shield size={18} />
                  Search Prior Art
                </>
              )}
            </button>
          </div>
        </form>
      </div>
      
      {/* Error */}
      {searchMutation.isError && (
        <div className="p-4 bg-red-50 text-red-700 rounded-lg mb-6 flex items-center gap-2">
          <AlertTriangle size={20} />
          Search failed: {searchMutation.error?.message}
        </div>
      )}
      
      {/* Results */}
      {data && (
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Main results */}
          <div className="lg:col-span-2 space-y-4">
            {/* Stats */}
            <div className="grid grid-cols-3 gap-4">
              <div className="p-4 bg-blue-50 rounded-lg text-center">
                <div className="text-2xl font-bold text-blue-700">
                  {data.total_patents_searched}
                </div>
                <div className="text-xs text-blue-600">Patents Searched</div>
              </div>
              <div className="p-4 bg-orange-50 rounded-lg text-center">
                <div className="text-2xl font-bold text-orange-700">
                  {data.blocking_patents_found}
                </div>
                <div className="text-xs text-orange-600">Potential Blockers</div>
              </div>
              <div className="p-4 bg-purple-50 rounded-lg text-center">
                <div className="text-2xl font-bold text-purple-700">
                  {data.patents.filter(p => p.overall_risk === 'high').length}
                </div>
                <div className="text-xs text-purple-600">High Risk</div>
              </div>
            </div>
            
            {/* Patent list */}
            <div>
              <h2 className="text-lg font-semibold mb-4">
                Potentially Blocking Patents
              </h2>
              
              {data.patents.length === 0 ? (
                <div className="text-center py-12 bg-green-50 rounded-lg">
                  <CheckCircle className="mx-auto text-green-500 mb-2" size={32} />
                  <p className="text-green-700 font-medium">No significant prior art found</p>
                  <p className="text-sm text-green-600 mt-1">
                    Your invention appears to be novel based on our database
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {data.patents.map((patent, i) => (
                    <BlockingPatentCard key={i} patent={patent} />
                  ))}
                </div>
              )}
            </div>
          </div>
          
          {/* Analysis sidebar */}
          <div>
            <AnalysisPanel analysis={data.analysis} />
          </div>
        </div>
      )}
    </div>
  )
}
