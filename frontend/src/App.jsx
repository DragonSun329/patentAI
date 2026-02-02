import { useState } from 'react'
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import { Search, Upload, GitCompare, BarChart3, Menu, X, Download } from 'lucide-react'
import SearchPage from './pages/SearchPage'
import UploadPage from './pages/UploadPage'
import ComparePage from './pages/ComparePage'
import DashboardPage from './pages/DashboardPage'
import ImportPage from './pages/ImportPage'

function NavLink({ to, icon: Icon, children }) {
  const location = useLocation()
  const isActive = location.pathname === to
  
  return (
    <Link
      to={to}
      className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all ${
        isActive 
          ? 'bg-blue-600 text-white' 
          : 'text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800'
      }`}
    >
      <Icon size={18} />
      <span className="font-medium">{children}</span>
    </Link>
  )
}

function Layout({ children }) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center">
                <span className="text-white font-bold text-lg">P</span>
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900 dark:text-white">PatentAI</h1>
                <p className="text-xs text-gray-500 dark:text-gray-400">Infringement Detection</p>
              </div>
            </Link>
            
            {/* Desktop Nav */}
            <nav className="hidden md:flex items-center gap-2">
              <NavLink to="/search" icon={Search}>Search</NavLink>
              <NavLink to="/import" icon={Download}>Import</NavLink>
              <NavLink to="/upload" icon={Upload}>Upload</NavLink>
              <NavLink to="/compare" icon={GitCompare}>Compare</NavLink>
              <NavLink to="/dashboard" icon={BarChart3}>Dashboard</NavLink>
            </nav>
            
            {/* Mobile menu button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
          </div>
        </div>
        
        {/* Mobile Nav */}
        {mobileMenuOpen && (
          <nav className="md:hidden border-t border-gray-200 dark:border-gray-700 p-4 space-y-2">
            <NavLink to="/search" icon={Search}>Search</NavLink>
            <NavLink to="/import" icon={Download}>Import</NavLink>
            <NavLink to="/upload" icon={Upload}>Upload</NavLink>
            <NavLink to="/compare" icon={GitCompare}>Compare</NavLink>
            <NavLink to="/dashboard" icon={BarChart3}>Dashboard</NavLink>
          </nav>
        )}
      </header>
      
      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
    </div>
  )
}

function HomePage() {
  return (
    <div className="text-center py-16">
      <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-4">
        AI-Powered Patent Infringement Detection
      </h1>
      <p className="text-xl text-gray-600 dark:text-gray-300 mb-8 max-w-2xl mx-auto">
        Search patents with hybrid vector + fuzzy matching, compare documents, 
        and get AI-powered infringement risk analysis.
      </p>
      <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
        <Link to="/search" className="p-6 bg-white dark:bg-gray-800 rounded-2xl shadow-lg hover:shadow-xl transition-shadow">
          <Search className="w-12 h-12 text-blue-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Search</h3>
          <p className="text-gray-600 dark:text-gray-400 text-sm mt-2">
            Hybrid semantic + fuzzy search across patent database
          </p>
        </Link>
        <Link to="/compare" className="p-6 bg-white dark:bg-gray-800 rounded-2xl shadow-lg hover:shadow-xl transition-shadow">
          <GitCompare className="w-12 h-12 text-purple-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Compare</h3>
          <p className="text-gray-600 dark:text-gray-400 text-sm mt-2">
            LLM-powered infringement analysis between patents
          </p>
        </Link>
        <Link to="/dashboard" className="p-6 bg-white dark:bg-gray-800 rounded-2xl shadow-lg hover:shadow-xl transition-shadow">
          <BarChart3 className="w-12 h-12 text-green-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Dashboard</h3>
          <p className="text-gray-600 dark:text-gray-400 text-sm mt-2">
            Analytics, metrics, and system health monitoring
          </p>
        </Link>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/import" element={<ImportPage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/compare" element={<ComparePage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}
