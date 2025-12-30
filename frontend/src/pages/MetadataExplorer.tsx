import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Database, Search, Loader2, RefreshCw, ChevronDown, ChevronRight } from 'lucide-react'
import { tableAPI } from '../api/client'

export default function MetadataExplorer() {
  const [expandedTable, setExpandedTable] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const queryClient = useQueryClient()

  // Get all tables
  const { data: tables, isLoading } = useQuery({
    queryKey: ['tables'],
    queryFn: tableAPI.list,
  })

  // Sync metadata mutation
  const syncMutation = useMutation({
    mutationFn: () => tableAPI.syncMetadata(false),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tables'] })
    },
  })

  // Get table metadata
  const { data: tableMetadata } = useQuery({
    queryKey: ['table-metadata', expandedTable],
    queryFn: () => expandedTable ? tableAPI.getMetadata(expandedTable) : null,
    enabled: !!expandedTable,
  })

  const filteredTables = tables?.filter((table) =>
    table.table_name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="flex flex-col h-full bg-slate-900">
      {/* Header */}
      <div className="bg-slate-800 border-b border-slate-700 p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-white">Metadata Explorer</h2>
            <p className="text-slate-400 mt-1">
              Browse database tables and AI-generated descriptions
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

      <div className="flex-1 overflow-auto p-6">
        <div className="max-w-6xl mx-auto space-y-6">
          {/* Search */}
          <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search tables..."
                className="w-full bg-slate-700 text-white rounded-lg pl-10 pr-4 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
          </div>

          {/* Tables List */}
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
            </div>
          ) : filteredTables && filteredTables.length > 0 ? (
            <div className="space-y-3">
              {filteredTables.map((table) => (
                <div
                  key={table.table_name}
                  className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden"
                >
                  {/* Table Header */}
                  <button
                    onClick={() =>
                      setExpandedTable(
                        expandedTable === table.table_name ? null : table.table_name
                      )
                    }
                    className="w-full flex items-center justify-between p-4 hover:bg-slate-700 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <Database className="w-5 h-5 text-primary-400" />
                      <span className="text-white font-medium">{table.table_name}</span>
                      <span className="text-sm text-slate-400">{table.schema}</span>
                    </div>
                    {expandedTable === table.table_name ? (
                      <ChevronDown className="w-5 h-5 text-slate-400" />
                    ) : (
                      <ChevronRight className="w-5 h-5 text-slate-400" />
                    )}
                  </button>

                  {/* Table Details */}
                  {expandedTable === table.table_name && tableMetadata && (
                    <div className="border-t border-slate-700 p-4 space-y-4">
                      {/* Description */}
                      {tableMetadata.description && (
                        <div>
                          <h4 className="text-sm font-medium text-slate-300 mb-2">
                            Description
                          </h4>
                          <p className="text-sm text-slate-400">
                            {tableMetadata.description}
                          </p>
                        </div>
                      )}

                      {/* Columns */}
                      {tableMetadata.columns && (
                        <div>
                          <h4 className="text-sm font-medium text-slate-300 mb-2">
                            Columns ({tableMetadata.columns.length})
                          </h4>
                          <div className="bg-slate-900 rounded p-3 space-y-2">
                            {tableMetadata.columns.map((column: any, idx: number) => (
                              <div
                                key={idx}
                                className="flex items-center justify-between text-sm"
                              >
                                <span className="text-white font-mono">
                                  {column.column_name}
                                </span>
                                <span className="text-primary-400 text-xs">
                                  {column.data_type}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Sample Data */}
                      {tableMetadata.sample_data && tableMetadata.sample_data.length > 0 && (
                        <div>
                          <h4 className="text-sm font-medium text-slate-300 mb-2">
                            Sample Data
                          </h4>
                          <div className="bg-slate-900 rounded p-3 overflow-x-auto">
                            <table className="w-full text-sm">
                              <thead>
                                <tr className="border-b border-slate-700">
                                  {Object.keys(tableMetadata.sample_data[0]).map((key) => (
                                    <th
                                      key={key}
                                      className="text-left text-slate-400 font-medium py-2 pr-4"
                                    >
                                      {key}
                                    </th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody>
                                {tableMetadata.sample_data.slice(0, 3).map((row: any, idx: number) => (
                                  <tr key={idx} className="border-b border-slate-800">
                                    {Object.values(row).map((value: any, vidx: number) => (
                                      <td key={vidx} className="text-slate-300 py-2 pr-4">
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
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-slate-400">
              <Database className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>No tables found</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
