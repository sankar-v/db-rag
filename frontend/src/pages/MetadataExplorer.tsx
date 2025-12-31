import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Database, Search, Loader2, RefreshCw, Table2, ChevronDown, ChevronRight } from 'lucide-react'
import { metadataAPI, connectionAPI } from '../api/client'

export default function MetadataExplorer() {
  const [selectedTableName, setSelectedTableName] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [expandedDatabases, setExpandedDatabases] = useState<Set<string>>(new Set())
  const queryClient = useQueryClient()

  // Get all connections
  const { data: connections } = useQuery({
    queryKey: ['connections'],
    queryFn: connectionAPI.list,
  })

  // Get all metadata tables
  const { data: tables, isLoading } = useQuery({
    queryKey: ['metadata-tables'],
    queryFn: metadataAPI.listTables,
  })

  // Sync metadata mutation
  const syncMutation = useMutation({
    mutationFn: () => metadataAPI.syncMetadata(false),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['metadata-tables'] })
    },
  })

  // Get table metadata for selected table
  const { data: tableMetadata } = useQuery({
    queryKey: ['table-metadata', selectedTableName],
    queryFn: () => selectedTableName ? metadataAPI.getTableMetadata(selectedTableName) : null,
    enabled: !!selectedTableName,
  })

  // Group tables by database (using connection info from metadata)
  const groupedTables = tables?.reduce((acc: any, table: any) => {
    // Find the connection for this table (tables come from active connection)
    const activeConnection = connections?.find((c: any) => c.is_active)
    const dbName = activeConnection?.database || 'Unknown Database'
    
    if (!acc[dbName]) {
      acc[dbName] = {
        connection: activeConnection,
        tables: []
      }
    }
    acc[dbName].tables.push(table)
    return acc
  }, {}) || {}

  // Filter tables across all databases
  const filteredGroupedTables = Object.entries(groupedTables).reduce((acc: any, [dbName, data]: any) => {
    const filteredTables = data.tables.filter((table: any) =>
      table?.table_name?.toLowerCase().includes(searchQuery.toLowerCase())
    )
    if (filteredTables.length > 0) {
      acc[dbName] = { ...data, tables: filteredTables }
    }
    return acc
  }, {})

  // Auto-expand first database and select first table (only once when data loads)
  useEffect(() => {
    if (Object.keys(filteredGroupedTables).length > 0 && expandedDatabases.size === 0) {
      const firstDb = Object.keys(filteredGroupedTables)[0]
      setExpandedDatabases(new Set([firstDb]))
      if (!selectedTableName && filteredGroupedTables[firstDb].tables.length > 0) {
        setSelectedTableName(filteredGroupedTables[firstDb].tables[0].table_name)
      }
    }
  }, [tables]) // Only run when tables data changes

  const toggleDatabase = (dbName: string) => {
    setExpandedDatabases(prev => {
      const newExpanded = new Set(prev)
      if (newExpanded.has(dbName)) {
        newExpanded.delete(dbName)
      } else {
        newExpanded.add(dbName)
      }
      return newExpanded
    })
  }

  const handleSelectTable = (tableName: string) => {
    setSelectedTableName(tableName)
  }

  const totalTables = Object.values(filteredGroupedTables).reduce((sum: number, data: any) => sum + data.tables.length, 0)

  return (
    <div className="flex flex-col h-full bg-slate-900">
      {/* Header */}
      <div className="bg-slate-800 border-b border-slate-700 p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-white">Metadata Explorer</h2>
            <p className="text-slate-400 mt-1">
              Browse synced table metadata from control plane
            </p>
          </div>

          <button
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isPending}
            className="bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {syncMutation.isPending ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Syncing...
              </>
            ) : (
              <>
                <RefreshCw className="w-5 h-5" />
                Sync Metadata
              </>
            )}
          </button>
        </div>
      </div>

      {/* Content: Sidebar + Details */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar - Metadata Tables List */}
        <div className="w-80 bg-slate-800 border-r border-slate-700 overflow-y-auto">
          <div className="p-4">
            {/* Search */}
            <div className="mb-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search tables..."
                  className="w-full bg-slate-700 text-white rounded-lg pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>
            </div>

            <h3 className="text-sm font-semibold text-slate-400 uppercase mb-3">
              Databases & Tables ({totalTables} tables)
            </h3>

            {isLoading ? (
              <div className="text-slate-400 text-sm flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                Loading metadata...
              </div>
            ) : Object.keys(filteredGroupedTables).length > 0 ? (
              <div className="space-y-2">
                {Object.entries(filteredGroupedTables).map(([dbName, data]: any) => (
                  <div key={dbName} className="border border-slate-700 rounded-lg overflow-hidden">
                    {/* Database Header */}
                    <button
                      onClick={() => toggleDatabase(dbName)}
                      className="w-full flex items-center gap-2 p-3 bg-slate-700/50 hover:bg-slate-700 transition-colors"
                    >
                      {expandedDatabases.has(dbName) ? (
                        <ChevronDown className="w-4 h-4 text-slate-400" />
                      ) : (
                        <ChevronRight className="w-4 h-4 text-slate-400" />
                      )}
                      <Database className="w-5 h-5 text-primary-400" />
                      <div className="flex-1 text-left">
                        <div className="text-sm font-semibold text-white">{dbName}</div>
                        <div className="text-xs text-slate-400">
                          {data.tables.length} {data.tables.length === 1 ? 'table' : 'tables'}
                          {data.connection?.host && ` • ${data.connection.host}`}
                        </div>
                      </div>
                    </button>

                    {/* Tables List */}
                    {expandedDatabases.has(dbName) && (
                      <div className="bg-slate-800/50">
                        {data.tables.map((table: any) => {
                          const isSelected = table.table_name === selectedTableName

                          return (
                            <button
                              key={table.table_name}
                              onClick={() => handleSelectTable(table.table_name)}
                              className={`w-full flex items-start gap-3 p-3 pl-10 transition-colors text-left border-l-2 ${
                                isSelected
                                  ? 'bg-primary-600/20 border-primary-500'
                                  : 'hover:bg-slate-700/50 border-transparent'
                              }`}
                            >
                              <Table2 className={`w-4 h-4 flex-shrink-0 mt-0.5 ${isSelected ? 'text-primary-400' : 'text-slate-400'}`} />
                              <div className="flex-1 min-w-0">
                                <div className={`text-sm font-medium truncate ${isSelected ? 'text-white' : 'text-slate-300'}`}>
                                  {table.table_name}
                                </div>
                                <div className="text-xs text-slate-500 truncate">
                                  {table.schema}
                                </div>
                              </div>
                            </button>
                          )
                        })}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <Database className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                <p className="text-slate-400 text-sm mb-4">No metadata found</p>
                <p className="text-slate-500 text-xs">Sync metadata from your connections</p>
              </div>
            )}
          </div>
        </div>

        {/* Right Panel - Table Metadata Details */}
        <div className="flex-1 overflow-y-auto p-6">
          {selectedTableName && tableMetadata ? (
            <div className="max-w-4xl">
              {/* Table Header */}
              <div className="bg-slate-800 rounded-lg border border-slate-700 p-6 mb-6">
                <div className="flex items-start gap-4">
                  <div className="p-3 bg-primary-600/20 rounded-lg">
                    <Table2 className="w-8 h-8 text-primary-400" />
                  </div>
                  <div className="flex-1">
                    <h3 className="text-2xl font-bold text-white mb-2">
                      {selectedTableName}
                    </h3>
                    <div className="flex items-center gap-4 text-sm text-slate-400">
                      <span>Schema: {tableMetadata.schema || 'public'}</span>
                      {tableMetadata.columns && (
                        <span>• {tableMetadata.columns.length} columns</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Table Description */}
              {tableMetadata.description && (
                <div className="bg-slate-800 rounded-lg border border-slate-700 p-6 mb-6">
                  <h4 className="text-lg font-semibold text-white mb-3">Description</h4>
                  <p className="text-slate-300 leading-relaxed">
                    {tableMetadata.description}
                  </p>
                </div>
              )}

              {/* Columns */}
              {tableMetadata.columns && tableMetadata.columns.length > 0 && (
                <div className="bg-slate-800 rounded-lg border border-slate-700 p-6 mb-6">
                  <h4 className="text-lg font-semibold text-white mb-4">
                    Columns ({tableMetadata.columns.length})
                  </h4>
                  <div className="space-y-3">
                    {tableMetadata.columns.map((column: any, idx: number) => (
                      <div
                        key={idx}
                        className="bg-slate-900 rounded-lg p-4 border border-slate-700"
                      >
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-white font-mono font-medium">
                            {column.column_name}
                          </span>
                          <span className="text-primary-400 text-sm font-medium px-2 py-1 bg-primary-600/20 rounded">
                            {column.data_type}
                          </span>
                        </div>
                        {column.description && (
                          <p className="text-sm text-slate-400 mt-2">
                            {column.description}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Sample Data */}
              {tableMetadata.sample_data && tableMetadata.sample_data.length > 0 && (
                <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
                  <h4 className="text-lg font-semibold text-white mb-4">Sample Data</h4>
                  <div className="bg-slate-900 rounded-lg p-4 overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-slate-700">
                          {Object.keys(tableMetadata.sample_data[0]).map((key) => (
                            <th
                              key={key}
                              className="text-left text-slate-400 font-semibold py-3 pr-6 whitespace-nowrap"
                            >
                              {key}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {tableMetadata.sample_data.slice(0, 5).map((row: any, idx: number) => (
                          <tr key={idx} className="border-b border-slate-800">
                            {Object.values(row).map((value: any, vidx: number) => (
                              <td key={vidx} className="text-slate-300 py-3 pr-6 whitespace-nowrap">
                                {String(value)}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <Database className="w-16 h-16 text-slate-600 mx-auto mb-4" />
                <p className="text-slate-400 text-lg">Select a metadata table to view details</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
