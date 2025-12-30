import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  Database, 
  Plus, 
  Trash2, 
  Edit, 
  Power,
  CheckCircle2,
  XCircle
} from 'lucide-react'
import { connectionAPI } from '../api/client'
import ConnectionWizard from '../components/ConnectionWizard'
import { useContextStore } from '../store/contextStore'

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
  const [selectedConnectionId, setSelectedConnectionId] = useState<string | null>(null)
  const queryClient = useQueryClient()
  
  // Context store for chat
  const { selectedConnectionIds, toggleConnection } = useContextStore()

  // Get all connections
  const { data: connections, isLoading } = useQuery<Connection[]>({
    queryKey: ['connections'],
    queryFn: connectionAPI.list,
  })

  // Auto-select first connection if none selected
  const selectedConnection = connections?.find(c => c.id === selectedConnectionId) || connections?.[0]
  if (connections && connections.length > 0 && !selectedConnectionId) {
    setSelectedConnectionId(connections[0].id)
  }

  // Auto-enable active connection in context on first load
  useEffect(() => {
    if (connections && connections.length > 0 && selectedConnectionIds.length === 0) {
      const activeConnection = connections.find(c => c.is_active)
      if (activeConnection) {
        toggleConnection(activeConnection.id)
      }
    }
  }, [connections, selectedConnectionIds.length, toggleConnection])

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

  const handleSelectConnection = (id: string) => {
    setSelectedConnectionId(id)
  }

  const toggleExpanded = (id: string) => {
    // Not needed anymore, but keeping for compatibility
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
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar - Connection Tree */}
        <div className="w-80 bg-slate-800 border-r border-slate-700 overflow-y-auto">
          <div className="p-4">
            <h3 className="text-sm font-semibold text-slate-400 uppercase mb-3">
              Connections {selectedConnectionIds.length > 0 && `(${selectedConnectionIds.length} selected)`}
            </h3>
            {isLoading ? (
              <div className="text-slate-400 text-sm">Loading connections...</div>
            ) : connections && connections.length > 0 ? (
              <div className="space-y-1">
                {connections.map((connection) => {
                  const isSelected = connection.id === selectedConnectionId
                  const isInContext = selectedConnectionIds.includes(connection.id)
                  const StatusIcon =
                    connection.status === 'connected'
                      ? CheckCircle2
                      : connection.status === 'error'
                      ? XCircle
                      : XCircle

                  return (
                    <div
                      key={connection.id}
                      className={`flex items-center gap-2 p-3 rounded-lg transition-colors ${
                        isSelected
                          ? 'bg-primary-600/20 border border-primary-500'
                          : 'hover:bg-slate-700 border border-transparent'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={isInContext}
                        onChange={(e) => {
                          e.stopPropagation()
                          toggleConnection(connection.id)
                        }}
                        className="w-4 h-4 rounded border-slate-600 bg-slate-700 text-primary-600 focus:ring-primary-500 focus:ring-offset-0 cursor-pointer"
                        title="Include in chat context"
                      />
                      <button
                        onClick={() => handleSelectConnection(connection.id)}
                        className="flex-1 flex items-center gap-3 text-left min-w-0"
                      >
                        <Database className={`w-5 h-5 flex-shrink-0 ${isSelected ? 'text-primary-400' : 'text-slate-400'}`} />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className={`text-sm font-medium truncate ${isSelected ? 'text-white' : 'text-slate-300'}`}>
                              {connection.name}
                            </span>
                            {connection.is_active && (
                              <span className="flex-shrink-0 w-2 h-2 rounded-full bg-green-500"></span>
                            )}
                          </div>
                          <div className="text-xs text-slate-500 truncate">
                            {connection.database}
                          </div>
                        </div>
                        <StatusIcon
                          className={`w-4 h-4 flex-shrink-0 ${
                            connection.status === 'connected'
                              ? 'text-green-500'
                              : 'text-slate-500'
                          }`}
                        />
                      </button>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="text-center py-8">
                <Database className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                <p className="text-slate-400 text-sm mb-4">No connections yet</p>
                <button
                  onClick={handleNewConnection}
                  className="text-primary-400 hover:text-primary-300 text-sm font-medium"
                >
                  Add your first connection
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Right Panel - Connection Details */}
        <div className="flex-1 overflow-y-auto p-6">
          {selectedConnection ? (
            <div className="max-w-4xl">
              {/* Connection Info Card */}
              <div className="bg-slate-800 rounded-lg border border-slate-700 p-6 mb-6">
                <div className="flex items-start justify-between mb-6">
                  <div className="flex items-center gap-4">
                    <div className="p-3 bg-primary-500/10 rounded-lg">
                      <Database className="w-8 h-8 text-primary-500" />
                    </div>
                    <div>
                      <h3 className="text-2xl font-bold text-white mb-1">{selectedConnection.name}</h3>
                      <p className="text-slate-400">
                        {selectedConnection.host}:{selectedConnection.port} / {selectedConnection.database}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {!selectedConnection.is_active && (
                      <button
                        onClick={() => handleActivateConnection(selectedConnection.id)}
                        disabled={activateMutation.isPending}
                        className="text-slate-400 hover:text-green-400 p-2 rounded-lg hover:bg-slate-700 transition-colors"
                        title="Set as active connection"
                      >
                        <Power className="w-5 h-5" />
                      </button>
                    )}
                    <button
                      onClick={() => handleEditConnection(selectedConnection)}
                      className="text-slate-400 hover:text-primary-400 p-2 rounded-lg hover:bg-slate-700 transition-colors"
                      title="Edit connection"
                    >
                      <Edit className="w-5 h-5" />
                    </button>
                    <button
                      onClick={() => handleDeleteConnection(selectedConnection.id)}
                      disabled={selectedConnection.is_active}
                      className={`p-2 rounded-lg transition-colors ${
                        selectedConnection.is_active
                          ? 'text-slate-600 cursor-not-allowed'
                          : 'text-slate-400 hover:text-red-400 hover:bg-slate-700'
                      }`}
                      title={selectedConnection.is_active ? 'Cannot delete active connection' : 'Delete connection'}
                    >
                      <Trash2 className="w-5 h-5" />
                    </button>
                  </div>
                </div>

                {/* Status Badge */}
                <div className="flex items-center gap-4 mb-6">
                  {selectedConnection.is_active && (
                    <span className="bg-green-500/20 text-green-400 text-sm px-3 py-1 rounded-full font-medium flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4" />
                      Active Connection
                    </span>
                  )}
                  <span className={`text-sm px-3 py-1 rounded-full font-medium ${
                    selectedConnection.status === 'connected'
                      ? 'bg-green-500/20 text-green-400'
                      : 'bg-red-500/20 text-red-400'
                  }`}>
                    {selectedConnection.status === 'connected' ? 'Connected' : 'Disconnected'}
                  </span>
                </div>

                {/* Connection Details Grid */}
                <div className="grid grid-cols-2 gap-6">
                  <div>
                    <div className="text-sm text-slate-400 mb-1">Username</div>
                    <div className="text-white font-medium">{selectedConnection.user}</div>
                  </div>
                  <div>
                    <div className="text-sm text-slate-400 mb-1">Schema</div>
                    <div className="text-white font-medium">{selectedConnection.schema}</div>
                  </div>
                  <div>
                    <div className="text-sm text-slate-400 mb-1">Tables</div>
                    <div className="text-white font-medium">{selectedConnection.tables_count || 0}</div>
                  </div>
                  <div>
                    <div className="text-sm text-slate-400 mb-1">Created</div>
                    <div className="text-white font-medium">
                      {new Date(selectedConnection.created_at).toLocaleDateString()}
                    </div>
                  </div>
                </div>
              </div>

              {/* Additional sections can go here - table list, sync options, etc. */}
            </div>
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <Database className="w-16 h-16 text-slate-600 mx-auto mb-4" />
                <p className="text-slate-400">Select a connection to view details</p>
              </div>
            </div>
          )}
        </div>
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
