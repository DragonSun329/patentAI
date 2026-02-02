import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Search, Loader2, AlertCircle, CheckCircle, XCircle } from 'lucide-react'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function RiskBadge({ score }) {
  if (score >= 0.8) {
    return <span className="px-2 py-1 bg-red-100 text-red-700 rounded-full text-xs font-medium">High Risk</span>
  } else if (score >= 0.6) {
    return <span className="px-2 py-1 bg-yellow-100 text-yellow-700 rounded-full text-xs font-medium">Medium Risk</span>
  }
  return <span className="px-2 py-1 bg-green-100 text-green-700 rounded-full text-xs font-medium">Low Risk</span>
}

function SearchResult({ result, onCompare }) {
  return (
    <div className="card mb-4 hover:shadow-xl transition-shadow">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              {result.patent.title}
            </h3>
            <RiskBadge score={result.combined_score} />
          </div>
          
          {result.patent.patent_number && (
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">
              Patent #{result.patent.patent_number}
            </p>
          )}
          
          <p className="text-gray-600 dark:text-gray-300 text-sm line-clamp-3">
            {result.patent.abstract}
          </p>
          
          <div className="flex items-center gap-4 mt-4 text-xs text-gray-500">
            <span>Vector: {(result.vector_score * 100).toFixed(1)}%</span>
            <span>Fuzzy: {(result.fuzzy_score * 100).toFixed(1)}%</span>
            <span className="font-medium text-blue-600">
              Combined: {(result.combined_score * 100).toFixed(1)}%
            </span>
          </div>
        </div>
        
        <button
          onClick={() => onCompare(result.patent.id)}
          className="btn-secondary text-sm"
        >
          Compare
        </button>
      </div>
    </div>
  )
}

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [vectorWeight, setVectorWeight] = useState(0.7)
  
  const searchMutation = useMutation({
    mutationFn: async (searchQuery) => {
      const response = await axios.post(`${API_URL}/patents/search`, {
        query: searchQuery,
        limit: 20,
        search_type: 'hybrid',
        vector_weight: vectorWeight
      })
      return response.data
    }
  })
  
  const handleSearch = (e) => {
    e.preventDefault()
    if (query.trim()) {
      searchMutation.mutate(query)
    }
  }
  
  const handleCompare = (patentId) => {
    // Navigate to compare page with selected patent
    window.location.href = `/compare?source=${patentId}`
  }
  
  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
          Patent Search
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          Search patents using hybrid vector + fuzzy matching
        </p>
      </div>
      
      {/* Search Form */}
      <form onSubmit={handleSearch} className="card mb-8">
        <div className="flex gap-4">
          <div className="flex-1">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search for patents by description, claims, or keywords..."
              className="input"
            />
          </div>
          <button
            type="submit"
            disabled={searchMutation.isPending}
            className="btn-primary flex items-center gap-2"
          >
            {searchMutation.isPending ? (
              <Loader2 className="animate-spin" size={18} />
            ) : (
              <Search size={18} />
            )}
            Search
          </button>
        </div>
        
        {/* Advanced Options */}
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <label className="text-sm text-gray-600 dark:text-gray-400">
            Vector Weight: {(vectorWeight * 100).toFixed(0)}% | Fuzzy: {((1-vectorWeight) * 100).toFixed(0)}%
          </label>
          <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={vectorWeight}
            onChange={(e) => setVectorWeight(parseFloat(e.target.value))}
            className="w-full mt-2"
          />
        </div>
      </form>
      
      {/* Error State */}
      {searchMutation.isError && (
        <div className="flex items-center gap-2 p-4 bg-red-50 text-red-700 rounded-lg mb-6">
          <AlertCircle size={20} />
          <span>Search failed: {searchMutation.error?.message}</span>
        </div>
      )}
      
      {/* Results */}
      {searchMutation.data && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              Results ({searchMutation.data.length})
            </h2>
          </div>
          
          {searchMutation.data.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              No patents found matching your query
            </div>
          ) : (
            searchMutation.data.map((result, index) => (
              <SearchResult
                key={result.patent.id || index}
                result={result}
                onCompare={handleCompare}
              />
            ))
          )}
        </div>
      )}
    </div>
  )
}
