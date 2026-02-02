import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Upload, Loader2, CheckCircle, AlertCircle } from 'lucide-react'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function UploadPage() {
  const [formData, setFormData] = useState({
    title: '',
    abstract: '',
    claims: '',
    patent_number: '',
    applicant: '',
    classification: ''
  })
  
  const uploadMutation = useMutation({
    mutationFn: async (data) => {
      const response = await axios.post(`${API_URL}/patents/`, data)
      return response.data
    }
  })
  
  const handleSubmit = (e) => {
    e.preventDefault()
    uploadMutation.mutate(formData)
  }
  
  const handleChange = (e) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }))
  }
  
  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
          Upload Patent
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          Add a new patent to the database with automatic embedding generation
        </p>
      </div>
      
      <form onSubmit={handleSubmit} className="card max-w-2xl">
        <div className="space-y-6">
          {/* Title */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Title *
            </label>
            <input
              type="text"
              name="title"
              value={formData.title}
              onChange={handleChange}
              required
              className="input"
              placeholder="Patent title"
            />
          </div>
          
          {/* Abstract */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Abstract *
            </label>
            <textarea
              name="abstract"
              value={formData.abstract}
              onChange={handleChange}
              required
              rows={4}
              className="input"
              placeholder="Patent abstract describing the invention..."
            />
          </div>
          
          {/* Claims */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Claims
            </label>
            <textarea
              name="claims"
              value={formData.claims}
              onChange={handleChange}
              rows={6}
              className="input"
              placeholder="Patent claims (one per line)..."
            />
          </div>
          
          {/* Patent Number */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Patent Number
              </label>
              <input
                type="text"
                name="patent_number"
                value={formData.patent_number}
                onChange={handleChange}
                className="input"
                placeholder="US12345678"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Classification (IPC/CPC)
              </label>
              <input
                type="text"
                name="classification"
                value={formData.classification}
                onChange={handleChange}
                className="input"
                placeholder="G06F17/30"
              />
            </div>
          </div>
          
          {/* Applicant */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Applicant
            </label>
            <input
              type="text"
              name="applicant"
              value={formData.applicant}
              onChange={handleChange}
              className="input"
              placeholder="Company or inventor name"
            />
          </div>
          
          {/* Submit */}
          <div className="pt-4">
            <button
              type="submit"
              disabled={uploadMutation.isPending}
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              {uploadMutation.isPending ? (
                <>
                  <Loader2 className="animate-spin" size={18} />
                  Processing...
                </>
              ) : (
                <>
                  <Upload size={18} />
                  Upload Patent
                </>
              )}
            </button>
          </div>
        </div>
      </form>
      
      {/* Success */}
      {uploadMutation.isSuccess && (
        <div className="mt-6 p-4 bg-green-50 text-green-700 rounded-lg flex items-center gap-2">
          <CheckCircle size={20} />
          <span>Patent uploaded successfully! ID: {uploadMutation.data?.id}</span>
        </div>
      )}
      
      {/* Error */}
      {uploadMutation.isError && (
        <div className="mt-6 p-4 bg-red-50 text-red-700 rounded-lg flex items-center gap-2">
          <AlertCircle size={20} />
          <span>Upload failed: {uploadMutation.error?.message}</span>
        </div>
      )}
    </div>
  )
}
