import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Database, Check, X, Loader2, RefreshCw } from 'lucide-react'
import { connectionAPI, queryAPI } from '../api/client'

export default function DatabaseConnections() {
  const [formData, setFormData] = useState({
    host: 'localhost',
    port: 5433,
    database: 'pagila',
    user: 'postgres',
    password: 'postgres',
    schema: 'public',
  })
  const [testResult, setTestResult] = useState<any>(null)
  const queryClient = useQueryClient()

  // Get current status
  const { data: status } = useQuery({
    queryKey: ['system-status'],
    queryFn: queryAPI.getStatus,
  })

  // Test connection mutation
  const testMutation = useMutation({
    mutationFn: connectionAPI.test,
    onSuccess: (data) => {
      setTestResult(data)
    },
  })

  // Configure connection mutation
  const configureMutation = useMutation({
    mutationFn: connectionAPI.configure,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['system-status'] })
      setTestResult(null)
    },
  })

  const handleTest = () => {
    testMutation.mutate(formData)
  }

  const handleConfigure = () => {
    configureMutation.mutate(formData)
  }

  return (
    <div className="flex flex-col h-full bg-slate-900">
      {/* Header */}
      <div className="bg-slate-800 border-b border-slate-700 p-6">
        <h2 className="text-2xl font-bold text-white">Database Connections</h2>
        <p className="text-slate-400 mt-1">
          Configure PostgreSQL database connection
        </p>
      </div>

      <div className="flex-1 overflow-auto p-6">
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Current Status */}
          <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Current Status</h3>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-slate-700 rounded p-4">
                <div className="flex items-center gap-2 mb-2">
                  <div className={`w-3 h-3 rounded-full ${status?.database_connected ? 'bg-green-500' : 'bg-red-500'}`} />
                  <span className="text-sm font-medium text-slate-300">Connection</span>
                </div>
                <p className="text-2xl font-bold text-white">
                  {status?.database_connected ? 'Connected' : 'Disconnected'}
                </p>
              </div>

              <div className="bg-slate-700 rounded p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Database className="w-4 h-4 text-primary-400" />
                  <span className="text-sm font-medium text-slate-300">Tables</span>
                </div>
                <p className="text-2xl font-bold text-white">
                  {status?.tables_count || 0}
                </p>
              </div>

              <div className="bg-slate-700 rounded p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Check className="w-4 h-4 text-primary-400" />
                  <span className="text-sm font-medium text-slate-300">Metadata Synced</span>
                </div>
                <p className="text-2xl font-bold text-white">
                  {status?.metadata_synced ? 'Yes' : 'No'}
                </p>
              </div>

              <div className="bg-slate-700 rounded p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Database className="w-4 h-4 text-primary-400" />
                  <span className="text-sm font-medium text-slate-300">Documents</span>
                </div>
                <p className="text-2xl font-bold text-white">
                  {status?.documents_count || 0}
                </p>
              </div>
            </div>
          </div>

          {/* Connection Form */}
          <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Connection Configuration</h3>

            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Host
                  </label>
                  <input
                    type="text"
                    value={formData.host}
                    onChange={(e) => setFormData({ ...formData, host: e.target.value })}
                    className="w-full bg-slate-700 text-white rounded px-4 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Port
                  </label>
                  <input
                    type="number"
                    value={formData.port}
                    onChange={(e) => setFormData({ ...formData, port: parseInt(e.target.value) })}
                    className="w-full bg-slate-700 text-white rounded px-4 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Database Name
                </label>
                <input
                  type="text"
                  value={formData.database}
                  onChange={(e) => setFormData({ ...formData, database: e.target.value })}
                  className="w-full bg-slate-700 text-white rounded px-4 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Username
                  </label>
                  <input
                    type="text"
                    value={formData.user}
                    onChange={(e) => setFormData({ ...formData, user: e.target.value })}
                    className="w-full bg-slate-700 text-white rounded px-4 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Password
                  </label>
                  <input
                    type="password"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    className="w-full bg-slate-700 text-white rounded px-4 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Schema
                </label>
                <input
                  type="text"
                  value={formData.schema}
                  onChange={(e) => setFormData({ ...formData, schema: e.target.value })}
                  className="w-full bg-slate-700 text-white rounded px-4 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>

              {/* Test Result */}
              {testResult && (
                <div className={`p-4 rounded-lg border ${
                  testResult.success
                    ? 'bg-green-500/10 border-green-500/30 text-green-400'
                    : 'bg-red-500/10 border-red-500/30 text-red-400'
                }`}>
                  <div className="flex items-center gap-2">
                    {testResult.success ? (
                      <Check className="w-5 h-5" />
                    ) : (
                      <X className="w-5 h-5" />
                    )}
                    <span className="font-medium">{testResult.message}</span>
                  </div>
                  {testResult.tables_count !== undefined && (
                    <p className="text-sm mt-2">
                      Found {testResult.tables_count} tables
                    </p>
                  )}
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-3">
                <button
                  onClick={handleTest}
                  disabled={testMutation.isPending}
                  className="flex-1 bg-slate-700 text-white px-6 py-3 rounded-lg hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {testMutation.isPending ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Testing...
                    </>
                  ) : (
                    <>
                      <RefreshCw className="w-5 h-5" />
                      Test Connection
                    </>
                  )}
                </button>

                <button
                  onClick={handleConfigure}
                  disabled={configureMutation.isPending || !testResult?.success}
                  className="flex-1 bg-primary-600 text-white px-6 py-3 rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {configureMutation.isPending ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Configuring...
                    </>
                  ) : (
                    <>
                      <Check className="w-5 h-5" />
                      Apply Configuration
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* Help Text */}
          <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Quick Start</h3>
            <div className="text-sm text-slate-300 space-y-2">
              <p>• Default Docker setup uses:</p>
              <p className="ml-4 font-mono text-primary-400">
                Host: localhost, Port: 5433, Database: pagila, User: postgres, Password: postgres
              </p>
              <p className="mt-4">• Test the connection before applying to verify credentials</p>
              <p>• After applying, the system will reconnect and sync metadata automatically</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
