import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Upload, FileText, Trash2, Loader2, Plus, Calendar, File, CheckCircle, AlertCircle, X, Package } from 'lucide-react'
import { documentAPI } from '../api/client'
import { useContextStore } from '../store/contextStore'

interface UploadStatus {
  filename: string
  status: 'uploading' | 'vectorizing' | 'complete' | 'error'
  progress?: string
  error?: string
  documentId?: string
}

export default function DocumentManager() {
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [uploadMode, setUploadMode] = useState<'text' | 'file'>('file')
  const [textContent, setTextContent] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null)
  const [uploadStatuses, setUploadStatuses] = useState<UploadStatus[]>([])
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const queryClient = useQueryClient()
  const { selectedDocumentIds, toggleDocument } = useContextStore()

  // Get documents
  const { data: documents, isLoading } = useQuery({
    queryKey: ['documents'],
    queryFn: () => documentAPI.list(50, 0),
  })

  // Auto-select first document if none selected
  const selectedDoc = documents?.find(d => d.id === selectedDocId) || documents?.[0]
  if (documents && documents.length > 0 && !selectedDocId) {
    setSelectedDocId(documents[0].id)
  }

  // Upload file mutation
  const uploadFileMutation = useMutation({
    mutationFn: documentAPI.upload,
    onSuccess: (documentId, file) => {
      // Update status to vectorizing
      setUploadStatuses(prev => prev.map(status => 
        status.filename === file.name 
          ? { ...status, status: 'vectorizing', progress: 'Creating embeddings...', documentId }
          : status
      ))
      
      // Wait a moment to simulate vectorization, then mark complete
      setTimeout(() => {
        setUploadStatuses(prev => prev.map(status => 
          status.filename === file.name 
            ? { ...status, status: 'complete', progress: 'Document ready' }
            : status
        ))
        
        // Auto-select the new document
        setSelectedDocId(documentId)
        
        // Clear status after 3 seconds
        setTimeout(() => {
          setUploadStatuses(prev => prev.filter(s => s.filename !== file.name))
        }, 3000)
        
        queryClient.invalidateQueries({ queryKey: ['documents'] })
      }, 1500)
    },
    onError: (error: any, file) => {
      setUploadStatuses(prev => prev.map(status => 
        status.filename === file.name 
          ? { ...status, status: 'error', error: error.message || 'Upload failed' }
          : status
      ))
    },
  })

  // Add text mutation
  const addTextMutation = useMutation({
    mutationFn: ({ content, metadata }: { content: string; metadata?: any }) =>
      documentAPI.add(content, metadata),
    onSuccess: (documentId) => {
      const filename = 'Text Document'
      
      // Add status
      setUploadStatuses(prev => [...prev, { 
        filename, 
        status: 'vectorizing', 
        progress: 'Creating embeddings...',
        documentId 
      }])
      
      // Mark complete after vectorization
      setTimeout(() => {
        setUploadStatuses(prev => prev.map(status => 
          status.filename === filename 
            ? { ...status, status: 'complete', progress: 'Document ready' }
            : status
        ))
        
        setSelectedDocId(documentId)
        setTextContent('')
        
        setTimeout(() => {
          setUploadStatuses(prev => prev.filter(s => s.filename !== filename))
        }, 3000)
        
        queryClient.invalidateQueries({ queryKey: ['documents'] })
      }, 1500)
    },
  })

  const handleFileSelect = (files: FileList | null) => {
    if (!files || files.length === 0) return
    setSelectedFiles(Array.from(files))
  }

  const handleUploadClick = () => {
    if (selectedFiles.length === 0) return

    selectedFiles.forEach((file) => {
      // Add initial status
      setUploadStatuses(prev => [...prev, {
        filename: file.name,
        status: 'uploading',
        progress: 'Uploading...'
      }])
      
      uploadFileMutation.mutate(file)
    })
    
    // Clear selected files
    setSelectedFiles([])
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    handleFileSelect(e.dataTransfer.files)
  }

  const handleTextSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!textContent.trim()) return

    addTextMutation.mutate({
      content: textContent,
      metadata: { source: 'manual_entry' },
    })
  }

  const handleSelectDocument = (id: string) => {
    setSelectedDocId(id)
  }

  const handleDeleteDocument = (id: string) => {
    // TODO: Implement delete mutation
    console.log('Delete document:', id)
  }

  return (
    <div className="flex flex-col h-full bg-slate-900">
      {/* Header */}
      <div className="bg-slate-800 border-b border-slate-700 p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-white">Document Manager</h2>
            <p className="text-slate-400 mt-1">
              Upload documents for semantic search and vectorization
            </p>
          </div>

          <button
            onClick={() => setShowUploadModal(true)}
            className="bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700 flex items-center gap-2"
          >
            <Upload className="w-5 h-5" />
            Upload Document
          </button>
        </div>
      </div>

      {/* Main Content: Sidebar + Details */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar - Document List */}
        <div className="w-80 bg-slate-800 border-r border-slate-700 overflow-y-auto">
          <div className="p-4">
            <h3 className="text-sm font-semibold text-slate-400 uppercase mb-3">
              Documents ({documents?.length || 0}) {selectedDocumentIds.length > 0 && `· ${selectedDocumentIds.length} selected`}
            </h3>
            
            {/* Upload Progress */}
            {uploadStatuses.length > 0 && (
              <div className="mb-4 space-y-2">
                {uploadStatuses.map((status, idx) => (
                  <div
                    key={idx}
                    className="bg-slate-700 rounded-lg p-3 border border-slate-600"
                  >
                    <div className="flex items-center gap-2 mb-1">
                      {status.status === 'uploading' && (
                        <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
                      )}
                      {status.status === 'vectorizing' && (
                        <Loader2 className="w-4 h-4 text-purple-400 animate-spin" />
                      )}
                      {status.status === 'complete' && (
                        <CheckCircle className="w-4 h-4 text-green-400" />
                      )}
                      {status.status === 'error' && (
                        <AlertCircle className="w-4 h-4 text-red-400" />
                      )}
                      <span className="text-sm font-medium text-white truncate flex-1">
                        {status.filename}
                      </span>
                    </div>
                    <div className="text-xs text-slate-400">
                      {status.status === 'uploading' && 'Uploading file...'}
                      {status.status === 'vectorizing' && 'Creating embeddings...'}
                      {status.status === 'complete' && 'Ready for search'}
                      {status.status === 'error' && (status.error || 'Upload failed')}
                    </div>
                  </div>
                ))}
              </div>
            )}
            
            {isLoading ? (
              <div className="text-slate-400 text-sm flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                Loading documents...
              </div>
            ) : documents && documents.length > 0 ? (
              <div className="space-y-1">
                {documents.map((doc) => {
                  const isSelected = doc.id === selectedDocId
                  const isInContext = selectedDocumentIds.includes(doc.id)
                  const metadata = typeof doc.metadata === 'string' ? JSON.parse(doc.metadata) : doc.metadata
                  const filename = metadata?.filename || 'Untitled Document'
                  const preview = doc.content.substring(0, 60) + (doc.content.length > 60 ? '...' : '')

                  return (
                    <div
                      key={doc.id}
                      className={`flex items-start gap-2 p-3 rounded-lg transition-colors ${
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
                          toggleDocument(doc.id)
                        }}
                        className="w-4 h-4 mt-1 rounded border-slate-600 bg-slate-700 text-primary-600 focus:ring-primary-500 focus:ring-offset-0 cursor-pointer"
                        title="Include in chat context"
                      />
                      <button
                        onClick={() => handleSelectDocument(doc.id)}
                        className="flex-1 flex items-start gap-3 text-left min-w-0"
                      >
                        <FileText className={`w-5 h-5 flex-shrink-0 mt-0.5 ${isSelected ? 'text-primary-400' : 'text-slate-400'}`} />
                        <div className="flex-1 min-w-0">
                          <div className={`text-sm font-medium truncate ${isSelected ? 'text-white' : 'text-slate-300'}`}>
                            {filename}
                          </div>
                          <div className="text-xs text-slate-500 line-clamp-2 mt-1">
                            {preview}
                          </div>
                          <div className="text-xs text-slate-600 mt-1 flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            {new Date(doc.created_at).toLocaleDateString()}
                          </div>
                        </div>
                      </button>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="text-center py-8">
                <FileText className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                <p className="text-slate-400 text-sm mb-4">No documents yet</p>
                <button
                  onClick={() => setShowUploadModal(true)}
                  className="text-primary-400 text-sm hover:text-primary-300"
                >
                  Upload your first document
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Right Panel - Document Details */}
        <div className="flex-1 overflow-y-auto p-6">
          {selectedDoc ? (
            <div className="max-w-4xl">
              {/* Document Header */}
              <div className="bg-slate-800 rounded-lg border border-slate-700 p-6 mb-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-start gap-4">
                    <div className="bg-primary-600/20 rounded-lg p-3">
                      <FileText className="w-8 h-8 text-primary-400" />
                    </div>
                    <div>
                      <h3 className="text-xl font-semibold text-white mb-1">
                        {(() => {
                          const metadata = typeof selectedDoc.metadata === 'string' 
                            ? JSON.parse(selectedDoc.metadata) 
                            : selectedDoc.metadata
                          return metadata?.filename || 'Untitled Document'
                        })()}
                      </h3>
                      <p className="text-slate-400 text-sm">
                        Uploaded {new Date(selectedDoc.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => handleDeleteDocument(selectedDoc.id)}
                    className="text-red-400 hover:text-red-300 p-2"
                    title="Delete document"
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>
                </div>

                {/* Metadata Grid */}
                <div className="grid grid-cols-2 gap-4">
                  {(() => {
                    const metadata = typeof selectedDoc.metadata === 'string' 
                      ? JSON.parse(selectedDoc.metadata) 
                      : selectedDoc.metadata
                    
                    return (
                      <>
                        <div className="bg-slate-700/50 rounded p-3">
                          <div className="text-xs text-slate-400 mb-1">Source</div>
                          <div className="text-sm text-white">{metadata?.source || 'Unknown'}</div>
                        </div>
                        <div className="bg-slate-700/50 rounded p-3">
                          <div className="text-xs text-slate-400 mb-1">File Type</div>
                          <div className="text-sm text-white uppercase">{metadata?.file_type || 'text'}</div>
                        </div>
                        <div className="bg-slate-700/50 rounded p-3">
                          <div className="text-xs text-slate-400 mb-1">Size</div>
                          <div className="text-sm text-white">
                            {metadata?.size_bytes 
                              ? `${(metadata.size_bytes / 1024).toFixed(1)} KB` 
                              : 'N/A'}
                          </div>
                        </div>
                        <div className="bg-slate-700/50 rounded p-3">
                          <div className="text-xs text-slate-400 mb-1">Status</div>
                          <div className="flex items-center gap-2">
                            {metadata?.is_chunked ? (
                              <>
                                <Package className="w-4 h-4 text-purple-400" />
                                <span className="text-sm text-white">Chunked</span>
                              </>
                            ) : (
                              <>
                                <CheckCircle className="w-4 h-4 text-green-400" />
                                <span className="text-sm text-white">Vectorized</span>
                              </>
                            )}
                          </div>
                        </div>
                      </>
                    )
                  })()}
                </div>
              </div>

              {/* Chunks Information */}
              {(() => {
                const metadata = typeof selectedDoc.metadata === 'string' 
                  ? JSON.parse(selectedDoc.metadata) 
                  : selectedDoc.metadata
                
                if (metadata?.is_chunked && metadata?.chunk_ids) {
                  return (
                    <div className="bg-slate-800 rounded-lg border border-slate-700 p-6 mb-6">
                      <h4 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                        <Package className="w-5 h-5 text-purple-400" />
                        Document Chunks ({metadata.total_chunks})
                      </h4>
                      <p className="text-slate-400 text-sm mb-4">
                        This document was split into {metadata.total_chunks} chunks for efficient vectorization. Each chunk is searchable independently.
                      </p>
                      <div className="space-y-3">
                        {metadata.chunk_ids.map((chunk: any, idx: number) => (
                          <div key={idx} className="bg-slate-700/50 rounded-lg p-4">
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-sm font-medium text-white">
                                Chunk {chunk.index + 1} of {metadata.total_chunks}
                              </span>
                              <span className="text-xs text-slate-500">ID: {chunk.id.substring(0, 8)}...</span>
                            </div>
                            <div className="text-xs text-slate-400 bg-slate-800 rounded p-2 font-mono">
                              {chunk.preview}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )
                }
              })()}

              {/* Content Preview */}
              <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
                <h4 className="text-lg font-semibold text-white mb-4">Content Preview</h4>
                <div className="bg-slate-900 rounded-lg p-4 max-h-96 overflow-y-auto">
                  <pre className="text-sm text-slate-300 whitespace-pre-wrap font-mono">
                    {selectedDoc.content.substring(0, 2000)}
                    {selectedDoc.content.length > 2000 && '\n\n... (truncated)'}
                  </pre>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <FileText className="w-16 h-16 text-slate-600 mx-auto mb-4" />
                <p className="text-slate-400 text-lg mb-2">No document selected</p>
                <p className="text-slate-500 text-sm">Select a document from the list to view details</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-800 rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-6 border-b border-slate-700">
              <h3 className="text-xl font-semibold text-white">Upload Document</h3>
              <button
                onClick={() => {
                  setShowUploadModal(false)
                  setSelectedFiles([])
                  setTextContent('')
                }}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-6">
              {/* Mode Selector */}
              <div className="flex gap-2 mb-6">
                <button
                  onClick={() => setUploadMode('file')}
                  className={`flex-1 px-4 py-3 rounded-lg flex items-center justify-center gap-2 ${
                    uploadMode === 'file'
                      ? 'bg-primary-600 text-white'
                      : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                  }`}
                >
                  <Upload className="w-5 h-5" />
                  Upload Files
                </button>
                <button
                  onClick={() => setUploadMode('text')}
                  className={`flex-1 px-4 py-3 rounded-lg flex items-center justify-center gap-2 ${
                    uploadMode === 'text'
                      ? 'bg-primary-600 text-white'
                      : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                  }`}
                >
                  <Plus className="w-5 h-5" />
                  Add Text
                </button>
              </div>

              {/* File Upload */}
              {uploadMode === 'file' && (
                <div className="space-y-4">
                  <div
                    onDragOver={(e) => {
                      e.preventDefault()
                      setIsDragging(true)
                    }}
                    onDragLeave={() => setIsDragging(false)}
                    onDrop={handleDrop}
                    className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors ${
                      isDragging
                        ? 'border-primary-500 bg-primary-500/10'
                        : 'border-slate-600 hover:border-slate-500'
                    }`}
                  >
                    <Upload className="w-12 h-12 text-slate-400 mx-auto mb-4" />
                    <p className="text-white mb-2">
                      Drag and drop files here, or click to select
                    </p>
                    <p className="text-sm text-slate-400 mb-4">
                      Supports PDF, TXT, MD, CSV, JSON, XML files
                    </p>
                    <input
                      type="file"
                      multiple
                      onChange={(e) => handleFileSelect(e.target.files)}
                      className="hidden"
                      id="file-upload-modal"
                      accept=".txt,.md,.pdf,.csv,.json,.xml"
                    />
                    <label
                      htmlFor="file-upload-modal"
                      className="bg-slate-600 text-white px-6 py-2 rounded-lg cursor-pointer hover:bg-slate-500 inline-block"
                    >
                      Select Files
                    </label>
                  </div>

                  {/* Selected Files Display */}
                  {selectedFiles.length > 0 && (
                    <div className="bg-slate-700 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-3">
                        <h4 className="text-sm font-medium text-white">
                          Selected Files ({selectedFiles.length})
                        </h4>
                        <button
                          onClick={() => setSelectedFiles([])}
                          className="text-xs text-slate-400 hover:text-white"
                        >
                          Clear
                        </button>
                      </div>
                      <div className="space-y-2 mb-4">
                        {selectedFiles.map((file, idx) => (
                          <div
                            key={idx}
                            className="flex items-center gap-2 text-sm bg-slate-800 rounded p-2"
                          >
                            <File className="w-4 h-4 text-slate-400 flex-shrink-0" />
                            <span className="text-white flex-1 truncate">{file.name}</span>
                            <span className="text-slate-400 text-xs">
                              {(file.size / 1024).toFixed(1)} KB
                            </span>
                          </div>
                        ))}
                      </div>
                      <button
                        onClick={() => {
                          handleUploadClick()
                          setShowUploadModal(false)
                        }}
                        disabled={uploadFileMutation.isPending}
                        className="w-full bg-primary-600 text-white px-6 py-3 rounded-lg hover:bg-primary-700 disabled:bg-slate-600 disabled:cursor-not-allowed flex items-center justify-center gap-2 font-medium"
                      >
                        {uploadFileMutation.isPending ? (
                          <>
                            <Loader2 className="w-5 h-5 animate-spin" />
                            Uploading...
                          </>
                        ) : (
                          <>
                            <Upload className="w-5 h-5" />
                            Upload {selectedFiles.length} {selectedFiles.length === 1 ? 'File' : 'Files'}
                          </>
                        )}
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* Text Upload */}
              {uploadMode === 'text' && (
                <form onSubmit={handleTextSubmit} className="space-y-4">
                  <textarea
                    value={textContent}
                    onChange={(e) => setTextContent(e.target.value)}
                    placeholder="Paste or type your document content here..."
                    className="w-full h-96 bg-slate-700 text-white rounded-lg p-4 focus:outline-none focus:ring-2 focus:ring-primary-500 font-mono text-sm"
                  />
                  <button
                    type="submit"
                    disabled={!textContent.trim() || addTextMutation.isPending}
                    className="w-full bg-primary-600 text-white px-6 py-3 rounded-lg hover:bg-primary-700 disabled:bg-slate-600 disabled:cursor-not-allowed flex items-center justify-center gap-2 font-medium"
                  >
                    {addTextMutation.isPending ? (
                      <>
                        <Loader2 className="w-5 h-5 animate-spin" />
                        Adding Document...
                      </>
                    ) : (
                      <>
                        <Plus className="w-5 h-5" />
                        Add Document
                      </>
                    )}
                  </button>
                </form>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
