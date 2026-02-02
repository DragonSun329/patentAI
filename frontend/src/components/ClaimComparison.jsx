import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Loader2, AlertTriangle, CheckCircle, XCircle, ChevronDown, ChevronUp, Zap } from 'lucide-react'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function RiskBadge({ level }) {
  const config = {
    high: { color: 'bg-red-100 text-red-700', label: 'High' },
    medium: { color: 'bg-yellow-100 text-yellow-700', label: 'Medium' },
    low: { color: 'bg-green-100 text-green-700', label: 'Low' },
    unknown: { color: 'bg-gray-100 text-gray-700', label: 'Unknown' },
  }
  const { color, label } = config[level] || config.unknown
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${color}`}>
      {label}
    </span>
  )
}

function ClaimCard({ claim, type }) {
  const [expanded, setExpanded] = useState(false)
  const isSource = type === 'source'
  
  return (
    <div className={`p-3 rounded-lg border ${isSource ? 'border-blue-200 bg-blue-50/50' : 'border-purple-200 bg-purple-50/50'}`}>
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className={`text-sm font-bold ${isSource ? 'text-blue-700' : 'text-purple-700'}`}>
            Claim {claim.claim_number}
          </span>
          {claim.is_independent ? (
            <span className="text-xs px-1.5 py-0.5 bg-white rounded border">Independent</span>
          ) : (
            <span className="text-xs px-1.5 py-0.5 bg-gray-100 rounded">→ Claim {claim.parent_claim_number}</span>
          )}
          {claim.claim_type && (
            <span className="text-xs text-gray-500 capitalize">{claim.claim_type}</span>
          )}
        </div>
        <button 
          onClick={() => setExpanded(!expanded)}
          className="p-1 hover:bg-white rounded"
        >
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
      </div>
      
      <p className={`text-sm text-gray-700 ${expanded ? '' : 'line-clamp-3'}`}>
        {claim.claim_text}
      </p>
      
      {claim.key_elements?.length > 0 && expanded && (
        <div className="mt-2 flex flex-wrap gap-1">
          {claim.key_elements.map((el, i) => (
            <span key={i} className="text-xs px-1.5 py-0.5 bg-white rounded border text-gray-600">
              {el}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

function MatchCard({ match, index }) {
  const [expanded, setExpanded] = useState(index === 0)
  
  return (
    <div className="border rounded-lg overflow-hidden">
      {/* Header */}
      <button 
        onClick={() => setExpanded(!expanded)}
        className="w-full p-4 flex items-center justify-between bg-gray-50 hover:bg-gray-100 transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="text-lg font-semibold text-gray-700">
            #{index + 1}
          </span>
          <div className="text-left">
            <div className="flex items-center gap-2">
              <span className="text-sm">
                Claim {match.source_claim.claim_number} ↔ Claim {match.target_claim.claim_number}
              </span>
              <RiskBadge level={match.risk_level} />
            </div>
            <div className="text-sm text-gray-500">
              {(match.similarity * 100).toFixed(1)}% similarity
            </div>
          </div>
        </div>
        {expanded ? <ChevronUp /> : <ChevronDown />}
      </button>
      
      {/* Expanded Content */}
      {expanded && (
        <div className="p-4 space-y-4">
          {/* Side by side claims */}
          <div className="grid md:grid-cols-2 gap-4">
            <ClaimCard claim={match.source_claim} type="source" />
            <ClaimCard claim={match.target_claim} type="target" />
          </div>
          
          {/* Similarity bar */}
          <div>
            <div className="flex justify-between text-xs text-gray-500 mb-1">
              <span>Similarity</span>
              <span>{(match.similarity * 100).toFixed(1)}%</span>
            </div>
            <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
              <div 
                className={`h-full transition-all ${
                  match.similarity >= 0.8 ? 'bg-red-500' :
                  match.similarity >= 0.6 ? 'bg-yellow-500' : 'bg-green-500'
                }`}
                style={{ width: `${match.similarity * 100}%` }}
              />
            </div>
          </div>
          
          {/* LLM Assessment */}
          {match.overlap_assessment && (
            <div className="p-3 bg-amber-50 rounded-lg">
              <div className="flex items-center gap-2 mb-1">
                <Zap size={14} className="text-amber-600" />
                <span className="text-sm font-medium text-amber-700">AI Assessment</span>
              </div>
              <p className="text-sm text-amber-800">{match.overlap_assessment}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function ClaimComparison({ sourcePatentId, targetPatentId }) {
  const compareMutation = useMutation({
    mutationFn: async () => {
      const response = await axios.post(`${API_URL}/claims/compare`, {
        source_patent_id: sourcePatentId,
        target_patent_id: targetPatentId,
        include_llm_analysis: true
      })
      return response.data
    }
  })
  
  // Auto-run when component mounts with valid IDs
  useState(() => {
    if (sourcePatentId && targetPatentId) {
      compareMutation.mutate()
    }
  }, [sourcePatentId, targetPatentId])
  
  if (!sourcePatentId || !targetPatentId) {
    return (
      <div className="text-center py-8 text-gray-500">
        Select two patents to compare at the claim level
      </div>
    )
  }
  
  if (compareMutation.isPending) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="animate-spin mr-2" />
        <span>Analyzing claims...</span>
      </div>
    )
  }
  
  if (compareMutation.isError) {
    return (
      <div className="p-4 bg-red-50 text-red-700 rounded-lg">
        Failed to analyze claims: {compareMutation.error?.message}
      </div>
    )
  }
  
  if (!compareMutation.data) {
    return (
      <button
        onClick={() => compareMutation.mutate()}
        className="btn-primary w-full"
      >
        Run Claim-Level Analysis
      </button>
    )
  }
  
  const data = compareMutation.data
  
  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 bg-blue-50 rounded-lg text-center">
          <div className="text-2xl font-bold text-blue-700">{data.source_claims_count}</div>
          <div className="text-xs text-blue-600">Source Claims</div>
        </div>
        <div className="p-4 bg-purple-50 rounded-lg text-center">
          <div className="text-2xl font-bold text-purple-700">{data.target_claims_count}</div>
          <div className="text-xs text-purple-600">Target Claims</div>
        </div>
        <div className="p-4 bg-orange-50 rounded-lg text-center">
          <div className="text-2xl font-bold text-orange-700">{data.independent_claims_at_risk}</div>
          <div className="text-xs text-orange-600">Independent at Risk</div>
        </div>
        <div className="p-4 bg-gray-50 rounded-lg text-center">
          <div className="text-2xl font-bold text-gray-700">{(data.highest_similarity * 100).toFixed(0)}%</div>
          <div className="text-xs text-gray-600">Highest Match</div>
        </div>
      </div>
      
      {/* Overall Risk */}
      <div className={`p-4 rounded-lg flex items-center gap-3 ${
        data.overall_risk === 'high' ? 'bg-red-50' :
        data.overall_risk === 'medium' ? 'bg-yellow-50' : 'bg-green-50'
      }`}>
        {data.overall_risk === 'high' ? (
          <XCircle className="text-red-500" size={24} />
        ) : data.overall_risk === 'medium' ? (
          <AlertTriangle className="text-yellow-500" size={24} />
        ) : (
          <CheckCircle className="text-green-500" size={24} />
        )}
        <div>
          <div className={`font-semibold ${
            data.overall_risk === 'high' ? 'text-red-700' :
            data.overall_risk === 'medium' ? 'text-yellow-700' : 'text-green-700'
          }`}>
            {data.overall_risk.toUpperCase()} RISK - Claim-Level Analysis
          </div>
          <div className={`text-sm ${
            data.overall_risk === 'high' ? 'text-red-600' :
            data.overall_risk === 'medium' ? 'text-yellow-600' : 'text-green-600'
          }`}>
            {data.summary || `Analyzed ${data.top_matches.length} potential claim overlaps`}
          </div>
        </div>
      </div>
      
      {/* Recommendation */}
      {data.recommendation && (
        <div className="p-4 bg-blue-50 rounded-lg">
          <div className="font-semibold text-blue-700 mb-1">Recommendation</div>
          <p className="text-blue-600 text-sm">{data.recommendation}</p>
        </div>
      )}
      
      {/* Top Matches */}
      {data.top_matches?.length > 0 ? (
        <div>
          <h3 className="text-lg font-semibold mb-4">
            Top Claim Matches ({data.top_matches.length})
          </h3>
          <div className="space-y-4">
            {data.top_matches.map((match, i) => (
              <MatchCard key={i} match={match} index={i} />
            ))}
          </div>
        </div>
      ) : (
        <div className="text-center py-8 text-gray-500">
          No significant claim overlaps found
        </div>
      )}
    </div>
  )
}
