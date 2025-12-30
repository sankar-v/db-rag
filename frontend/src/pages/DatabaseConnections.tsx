import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  Database, 
  Plus, 
  Trash2, 
  Edit, 
  Power,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  XCircle
} from 'lucide-react'
import { connectionAPI } from '../api/client'
import ConnectionWizard from '../components/ConnectionWizard'

interface Connection {
  id: string
  name: string
  host: string
  port: number
  database: string
  user: string
  schema: string
  is_active: boolean
  status: 'connected' | 'disconnected' | 'error'
  tables_count?: number
  created_at: string
}

export default function DatabaseConnections() {
  const [showWizard, setShowWizard] = useState(false)
  const [editingConnection, setEditingConnection] = useState<Connection | null>(null)
  const [expandedConnections, setExpandedConnections] = useState<Set<string>>(new Set())
  const queryClient = useQueryClient()

  // Get all connections
  const { data: connections, isLoading } = useQuery<Connection[]>({
    queryKey: ['connections'],
    queryFn: connectionAPI.list,
  })

  // Delete connection mutation
  const deleteMutation = useMutation({
    mutationFn: connectionAPI.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connections'] })
      queryClient.invalidateQueries({ queryKey: ['system-status'] })
    },
  })

  // Set active connection mutation
  const activateMutation = useMutation({
    mutationFn: connectionAPI.setActive,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connections'] })
      queryClient.invalidateQueries({ queryKey: ['system-status'] })
    },
  })

  const handleNewConnection = () => {
    setEditingConnection(null)
    setShowWizard(true)
  }

  const handleEditConnection = (connection: Connection) => {
    setEditingConnection(connection)
    setShowWizard(true)
  }

  const handleDeleteConnection = (id: string) => {
    if (confirm('Are you sure you want to delete this connection?')) {
      deleteMutation.mutate(id)
    }
  }

  const handleActivateConnection = (id: string) => {
    activateMutation.mutate(id)
  }

  const toggleExpanded = (id: string) => {
    setExpandedConnections((prev) => {
      const newSet = new Set(prev)
      if (newSet.has(id)) {
        newSet.delete(id)
      } else {
        newSet.add(id)
      }
      return newSet
    })
  }

  const handleWizardComplete = (connectionId: string) => {
    setShowWizard(false)
    setEditingConnection(null)
    queryClient.invalidateQueries({ queryKey: ['connections'] })
    queryClient.invalidateQueries({ queryKey: ['system-status'] })
    // Auto-activate the new connection
    activateMutation.mutate(connectionId)
  }

  return (
    <div className="flex flex-col h-full bg-slate-900">
      {/* Header */}
      <div className="bg-slate-800 border-b border-slate-700 p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-white">Database Connections</h2>
            <p className="text-slate-400 mt-1">
              Manage your database connections and switch between them
            </p>
          </div>

          <button
            onClick={handleNewConnection}
            className="bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700 flex items-center gap-2"
          >
            <Plus className="w-5 h-5" />
            New Connection
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-6">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-slate-400">Loading connections...</div>
          </div>
        ) : connections && connections.length > 0 ? (
          <div className="max-w-4xl mx-auto space-y-3">
            {connections.map((connection) => {
              const isExpanded = expandedConnections.has(connection.id)
              const StatusIcon =
                connection.status === 'connected'
                  ? CheckCircle2
                  : connection.status === 'error'
                  ? XCircle
                  : XCircle

              return (
                <div
                  key={connection.id}
                  className={`bg-slate-800 rounded-lg border transition-colors ${
                    connection.is_active
                      ? 'border-primary-500'
                      : 'border-slate-700'
                  }`}
                >
                  {/* Connection Header */}
                  <div className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3 flex-1">
                        <button
                          onClick={() => toggleExpanded(connection.id)}
                          className="text-slate-400 hover:text-white"
                        >
                          {isExpanded ? (
                            <ChevronDown className="w-5 h-5" />
                          ) : (
                            <ChevronRight className="w-5 h-5" />
                          )}
                        </button>

                        <Database className="w-6 h-6 text-primary-500" />

                        <div className="flex-1">
                          <div className="flex items-center gap-3">
                            <h3 className="text-lg font-semibold text-white">
                              {connection.name}
                            </h3>
                            {connection.is_active && (
                              <span className="bg-green-500/20 text-green-400 text-xs px-2 py-1 rounded-full font-medium">
                                Active
                              </span>
                            )}
                          </div>
                          <p className="text-sm text-slate-400 mt-1">
                            {connection.host}:{connection.port} / {connection.database}
                          </p>
                        </div>

                        <StatusIcon
                          className={`w-5 h-5 ${
                            connection.status === 'connected'
                              ? 'text-green-500'
                              : 'text-red-500'
                          }`}
                        />
                      </div>

                      <div className="flex items-center gap-2 ml-4">
                        {!connection.is_active && (
                          <button
                            onClick={() => handleActivateConnection(connection.id)}
                            disabled={activateMutation.isPending}
                            className="text-slate-400 hover:text-green-400 p-2 rounded-lg hover:bg-slate-700 transition-colors"
                            title="Set as active connection"
                          >
                            <Power className="w-4 h-4" />
                          </button>
                        )}
                        <button
                          onClick={() => handleEditConnection(connection)}
                          className="text-slate-400 hover:text-primary-400 p-2 rounded-lg hover:bg-slate-700 transition-colors"
                          title="Edit connection"
                        >
                          <Edit className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDeleteConnection(connection.id)}
                          disabled={connection.is_active || deleteMutation.isPending}
                          className="text-slate-400 hover:text-red-400 p-2 rounded-lg hover:bg-slate-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                          title="Delete connection"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Expanded Details */}
                  {isExpanded && (
                    <div className="border-t border-slate-700 p-4 bg-slate-750">
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-slate-400">Username:</span>
                          <span className="text-white ml-2">{connection.user}</span>
                        </div>
                        <div>
                          <span className="text-slate-400">Schema:</span>
                          <span className="text-white ml-2">{connection.schema}</span>
                        </div>
                        <div>
                          <span className="text-slate-400">Tables:</span>
                          <span className="text-white ml-2">
                            {connection.tables_count || 0}
                          </span>
                        </div>
                        <div>
                          <span className="text-slate-400">Created:</span>
                          <span className="text-white ml-2">
                            {new Date(connection.created_at).toLocaleDateString()}
                          </span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <Database className="w-20 h-20 text-slate-600 mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">
              No Connections Yet
            </h3>
            <p className="text-slate-400 mb-6 max-w-md">
              Get started by creating your first database connection. The wizard will
              guide you through the setup process.
            </p>
            <button
              onClick={handleNewConnection}
              className="bg-primary-600 text-white px-6 py-3 rounded-lg hover:bg-primary-700 flex items-center gap-2"
            >
              <Plus className="w-5 h-5" />
              Create First Connection
            </button>
          </div>
        )}
      </div>

      {/* Connection Wizard Modal */}
      {showWizard && (
        <ConnectionWizard
          onComplete={handleWizardComplete}
          onCancel={() => {
            setShowWizard(false)
            setEditingConnection(null)
          }}
          editConnection={editingConnection}
        />
      )}
    </div>
  )
}
