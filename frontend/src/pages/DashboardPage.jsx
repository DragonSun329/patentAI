import { useQuery } from '@tanstack/react-query'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts'
import { Activity, Database, Search, Clock, AlertTriangle, CheckCircle } from 'lucide-react'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function MetricCard({ icon: Icon, label, value, subtext, color = 'blue' }) {
  const colors = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    purple: 'bg-purple-50 text-purple-600',
    orange: 'bg-orange-50 text-orange-600',
  }
  
  return (
    <div className="card">
      <div className="flex items-center gap-4">
        <div className={`p-3 rounded-lg ${colors[color]}`}>
          <Icon size={24} />
        </div>
        <div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white">{value}</div>
          <div className="text-sm text-gray-500">{label}</div>
          {subtext && <div className="text-xs text-gray-400">{subtext}</div>}
        </div>
      </div>
    </div>
  )
}

export default function DashboardPage() {
  // Health check
  const healthQuery = useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      const response = await axios.get(`${API_URL}/health`)
      return response.data
    },
    refetchInterval: 30000
  })
  
  // Patents count
  const patentsQuery = useQuery({
    queryKey: ['patents-count'],
    queryFn: async () => {
      const response = await axios.get(`${API_URL}/patents/?limit=1000`)
      return response.data
    }
  })
  
  // Mock data for charts (in production, fetch from /metrics endpoint)
  const searchLatencyData = [
    { time: '00:00', latency: 120 },
    { time: '04:00', latency: 95 },
    { time: '08:00', latency: 180 },
    { time: '12:00', latency: 250 },
    { time: '16:00', latency: 200 },
    { time: '20:00', latency: 150 },
  ]
  
  const searchTypeData = [
    { type: 'Vector', count: 45 },
    { type: 'Fuzzy', count: 12 },
    { type: 'Hybrid', count: 89 },
  ]
  
  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
          Dashboard
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          System health and analytics overview
        </p>
      </div>
      
      {/* System Status */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-4">
          {healthQuery.data?.status === 'healthy' ? (
            <CheckCircle className="text-green-500" size={20} />
          ) : (
            <AlertTriangle className="text-yellow-500" size={20} />
          )}
          <span className="font-medium text-gray-900 dark:text-white">
            System Status: {healthQuery.data?.status || 'Loading...'}
          </span>
        </div>
      </div>
      
      {/* Metrics Grid */}
      <div className="grid md:grid-cols-4 gap-6 mb-8">
        <MetricCard
          icon={Database}
          label="Patents Indexed"
          value={patentsQuery.data?.length || 0}
          color="blue"
        />
        <MetricCard
          icon={Search}
          label="Searches Today"
          value="146"
          subtext="+23% from yesterday"
          color="green"
        />
        <MetricCard
          icon={Clock}
          label="Avg Latency"
          value="165ms"
          subtext="p95: 420ms"
          color="purple"
        />
        <MetricCard
          icon={Activity}
          label="Cache Hit Rate"
          value="78%"
          color="orange"
        />
      </div>
      
      {/* Charts */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Latency Chart */}
        <div className="card">
          <h3 className="font-semibold text-gray-900 dark:text-white mb-4">
            Search Latency (24h)
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={searchLatencyData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis />
              <Tooltip />
              <Line 
                type="monotone" 
                dataKey="latency" 
                stroke="#3b82f6" 
                strokeWidth={2}
                dot={{ fill: '#3b82f6' }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
        
        {/* Search Types Chart */}
        <div className="card">
          <h3 className="font-semibold text-gray-900 dark:text-white mb-4">
            Search Types
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={searchTypeData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="type" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="count" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
      
      {/* Prometheus Link */}
      <div className="mt-8 p-4 bg-gray-100 dark:bg-gray-800 rounded-lg">
        <h3 className="font-semibold text-gray-900 dark:text-white mb-2">
          Advanced Metrics
        </h3>
        <p className="text-gray-600 dark:text-gray-400 text-sm mb-3">
          For detailed metrics and alerting, access the Prometheus and Grafana dashboards:
        </p>
        <div className="flex gap-4">
          <a 
            href="http://localhost:9090" 
            target="_blank" 
            rel="noopener noreferrer"
            className="btn-secondary text-sm"
          >
            Prometheus →
          </a>
          <a 
            href="http://localhost:3001" 
            target="_blank" 
            rel="noopener noreferrer"
            className="btn-secondary text-sm"
          >
            Grafana →
          </a>
        </div>
      </div>
    </div>
  )
}
