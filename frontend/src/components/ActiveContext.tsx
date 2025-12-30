import { useState } from 'react'
import { Database, FileText, ChevronDown, ChevronUp, X } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { useContextStore } from '../store/contextStore'
import { connectionAPI, documentAPI } from '../api/client'

export default function ActiveContext() {
  const [isExpanded, setIsExpanded] = useState(false)
  const { selectedConnectionIds, selectedDocumentIds, clearAll } = useContextStore()

  const { data: connections } = useQuery({
    queryKey: ['connections'],
    queryFn: connectionAPI.list,
  })

  const { data: documents } = useQuery({
    queryKey: ['documents'],
    queryFn: () => documentAPI.list(100, 0),
  })

  const selectedConnections = connections?.filter((c) => selectedConnectionIds.includes(c.id)) || []
  const selectedDocuments = documents?.filter((d) => selectedDocumentIds.includes(d.id)) || []

  const totalSelected = selectedConnectionIds.length + selectedDocumentIds.length

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
          <div className="flex items-center gap-4">
            {selectedConnectionIds.length > 0 && (
              <div className="flex items-center gap-2 text-primary-400">
                <Database className="w-4 h-4" />
                <span className="text-sm font-medium">{selectedConnectionIds.length}</span>
              </div>
            )}
            {selectedDocumentIds.length > 0 && (
              <div className="flex items-center gap-2 text-green-400">
                <FileText className="w-4 h-4" />
                <span className="text-sm font-medium">{selectedDocumentIds.length}</span>
              </div>
            )}
          </div>
          <span className="text-sm text-slate-400">
            {totalSelected} {totalSelected === 1 ? 'item' : 'items'} in context
          </span>
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
                Connections
              </div>
              <div className="space-y-1">
                {selectedConnections.map((conn) => (
                  <div
                    key={conn.id}
                    className="flex items-center gap-2 text-sm text-slate-300 bg-slate-700/50 rounded px-2 py-1"
                  >
                    <span className="w-2 h-2 rounded-full bg-green-500" />
                    <span className="flex-1 truncate">{conn.name}</span>
                    <span className="text-xs text-slate-500">{conn.database}</span>
                  </div>
                ))}
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
