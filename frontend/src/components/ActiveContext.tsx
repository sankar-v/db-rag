import { useState, useRef } from 'react'
import { Database, FileText, ChevronDown, ChevronUp, X, Table2, ChevronLeft, ChevronRight } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { useContextStore } from '../store/contextStore'
import { connectionAPI, documentAPI, metadataAPI } from '../api/client'

export default function ActiveContext() {
  const [isExpanded, setIsExpanded] = useState(false)
  const [expandedConnections, setExpandedConnections] = useState<Set<string>>(new Set())
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const { selectedConnectionIds, selectedDocumentIds, clearAll } = useContextStore()

  const { data: connections } = useQuery({
    queryKey: ['connections'],
    queryFn: connectionAPI.list,
  })

  const { data: documents } = useQuery({
    queryKey: ['documents'],
    queryFn: () => documentAPI.list(100, 0),
  })

  const { data: tables } = useQuery({
    queryKey: ['tables'],
    queryFn: metadataAPI.listTables,
  })

  const selectedConnections = connections?.filter((c) => selectedConnectionIds.includes(c.id)) || []
  const selectedDocuments = documents?.filter((d) => selectedDocumentIds.includes(d.id)) || []
  
  // Count tables from selected connections
  const tableCount = tables?.length || 0

  const totalSelected = selectedConnectionIds.length + selectedDocumentIds.length

  // Scroll handler for horizontal table list
  const scroll = (direction: 'left' | 'right') => {
    if (scrollContainerRef.current) {
      const scrollAmount = 200
      scrollContainerRef.current.scrollBy({
        left: direction === 'left' ? -scrollAmount : scrollAmount,
        behavior: 'smooth'
      })
    }
  }

  // Toggle connection expansion
  const toggleConnection = (connectionId: string) => {
    setExpandedConnections(prev => {
      const newSet = new Set(prev)
      if (newSet.has(connectionId)) {
        newSet.delete(connectionId)
      } else {
        newSet.add(connectionId)
      }
      return newSet
    })
  }

  if (totalSelected === 0) {
    return (
      <div className="bg-slate-800 border border-slate-700 rounded-lg p-3 mb-4">
        <div className="flex items-center gap-2 text-slate-400 text-sm">
          <Database className="w-4 h-4" />
          <span>No context selected. Select connections or documents to include in your queries.</span>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg p-3 mb-4">
      {/* Summary Header */}
      <div className="flex items-center justify-between gap-3">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex-1 flex items-center gap-3 text-left hover:text-white transition-colors"
        >
          <div className="flex items-center gap-3 text-sm text-slate-400">
            {selectedConnectionIds.length > 0 && (
              <span>
                <span className="text-primary-400 font-medium">{selectedConnectionIds.length}</span> {selectedConnectionIds.length === 1 ? 'connection' : 'connections'}
              </span>
            )}
            {selectedConnectionIds.length > 0 && tableCount > 0 && (
              <span>
                • <span className="text-primary-400 font-medium">{tableCount}</span> {tableCount === 1 ? 'table' : 'tables'}
              </span>
            )}
            {selectedDocumentIds.length > 0 && (
              <span>
                • <span className="text-green-400 font-medium">{selectedDocumentIds.length}</span> {selectedDocumentIds.length === 1 ? 'document' : 'documents'}
              </span>
            )}
          </div>
          {isExpanded ? (
            <ChevronUp className="w-4 h-4 text-slate-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-slate-400" />
          )}
        </button>

        <button
          onClick={clearAll}
          className="px-3 py-1 text-xs bg-slate-700 hover:bg-slate-600 text-slate-300 rounded flex items-center gap-1.5 transition-colors"
          title="Clear all selections"
        >
          <X className="w-3 h-3" />
          Clear
        </button>
      </div>

      {/* Expanded Details */}
      {isExpanded && (
        <div className="mt-3 pt-3 border-t border-slate-700 space-y-3">
          {/* Connections */}
          {selectedConnections.length > 0 && (
            <div>
              <div className="flex items-center gap-2 text-primary-400 text-xs font-semibold uppercase mb-2">
                <Database className="w-3 h-3" />
                Connections & Tables
              </div>
              <div className="space-y-2">
                {selectedConnections.map((conn) => {
                  // Get tables for this connection (for now, show all tables)
                  const connectionTables = tables || []
                  const isConnectionExpanded = expandedConnections.has(conn.id)
                  
                  return (
                    <div key={conn.id} className="bg-slate-700/50 rounded overflow-hidden">
                      {/* Connection header - clickable */}
                      <button
                        onClick={() => toggleConnection(conn.id)}
                        className="w-full flex items-center gap-2 text-sm text-slate-300 px-2 py-2 hover:bg-slate-600/50 transition-colors"
                      >
                        {isConnectionExpanded ? (
                          <ChevronDown className="w-4 h-4 text-slate-400 flex-shrink-0" />
                        ) : (
                          <ChevronRight className="w-4 h-4 text-slate-400 flex-shrink-0" />
                        )}
                        <span className="w-2 h-2 rounded-full bg-green-500 flex-shrink-0" />
                        <span className="flex-1 truncate font-medium text-left">{conn.name}</span>
                        <span className="text-xs text-slate-500">{conn.database}</span>
                        <span className="text-xs text-slate-400">
                          {connectionTables.length} {connectionTables.length === 1 ? 'table' : 'tables'}
                        </span>
                      </button>
                      
                      {/* Horizontal scrollable tables list - collapsible */}
                      {isConnectionExpanded && connectionTables.length > 0 && (
                        <div className="relative group px-2 pb-2">
                          {/* Left scroll button */}
                          <button
                            onClick={() => scroll('left')}
                            className="absolute left-2 top-1/2 -translate-y-1/2 z-10 bg-slate-800/90 hover:bg-slate-700 p-1 rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                            aria-label="Scroll left"
                          >
                            <ChevronLeft className="w-3 h-3 text-slate-400" />
                          </button>
                          
                          {/* Tables container */}
                          <div
                            ref={scrollContainerRef}
                            className="flex gap-2 overflow-x-auto scrollbar-hide scroll-smooth px-6"
                            style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
                          >
                            {connectionTables.map((table) => (
                              <div
                                key={table.table_name}
                                className="flex items-center gap-1.5 bg-slate-600/50 hover:bg-slate-600 rounded px-2 py-1 text-xs text-slate-300 whitespace-nowrap transition-colors cursor-default"
                                title={`Table: ${table.table_name}`}
                              >
                                <Table2 className="w-3 h-3 flex-shrink-0" />
                                <span>{table.table_name}</span>
                              </div>
                            ))}
                          </div>
                          
                          {/* Right scroll button */}
                          <button
                            onClick={() => scroll('right')}
                            className="absolute right-2 top-1/2 -translate-y-1/2 z-10 bg-slate-800/90 hover:bg-slate-700 p-1 rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                            aria-label="Scroll right"
                          >
                            <ChevronRight className="w-3 h-3 text-slate-400" />
                          </button>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Documents */}
          {selectedDocuments.length > 0 && (
            <div>
              <div className="flex items-center gap-2 text-green-400 text-xs font-semibold uppercase mb-2">
                <FileText className="w-3 h-3" />
                Documents
              </div>
              <div className="space-y-1">
                {selectedDocuments.map((doc) => (
                  <div
                    key={doc.id}
                    className="flex items-center gap-2 text-sm text-slate-300 bg-slate-700/50 rounded px-2 py-1"
                  >
                    <FileText className="w-3 h-3 text-green-400" />
                    <span className="flex-1 truncate">
                      {doc.metadata?.filename || 'Untitled Document'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
