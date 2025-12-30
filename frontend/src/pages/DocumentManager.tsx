import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Upload, FileText, Trash2, Loader2, Plus } from 'lucide-react'
import { documentAPI } from '../api/client'

export default function DocumentManager() {
  const [uploadMode, setUploadMode] = useState<'text' | 'file'>('file')
  const [textContent, setTextContent] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  const queryClient = useQueryClient()

  // Get documents
  const { data: documents, isLoading } = useQuery({
    queryKey: ['documents'],
    queryFn: () => documentAPI.list(50, 0),
  })

  // Upload file mutation
  const uploadFileMutation = useMutation({
    mutationFn: documentAPI.upload,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] })
    },
  })

  // Add text mutation
  const addTextMutation = useMutation({
    mutationFn: ({ content, metadata }: { content: string; metadata?: any }) =>
      documentAPI.add(content, metadata),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      setTextContent('')
    },
  })

  const handleFileSelect = (files: FileList | null) => {
    if (!files || files.length === 0) return

    Array.from(files).forEach((file) => {
      uploadFileMutation.mutate(file)
    })
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

  return (
    <div className="flex flex-col h-full bg-slate-900">
      {/* Header */}
      <div className="bg-slate-800 border-b border-slate-700 p-6">
        <h2 className="text-2xl font-bold text-white">Document Manager</h2>
        <p className="text-slate-400 mt-1">
          Upload documents for semantic search and vectorization
        </p>
      </div>

      <div className="flex-1 overflow-auto p-6">
        <div className="max-w-6xl mx-auto space-y-6">
          {/* Upload Section */}
          <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Add Documents</h3>

            {/* Mode Selector */}
            <div className="flex gap-2 mb-4">
              <button
                onClick={() => setUploadMode('file')}
                className={`px-4 py-2 rounded ${
                  uploadMode === 'file'
                    ? 'bg-primary-600 text-white'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
              >
                <Upload className="w-4 h-4 inline mr-2" />
                Upload Files
              </button>
              <button
                onClick={() => setUploadMode('text')}
                className={`px-4 py-2 rounded ${
                  uploadMode === 'text'
                    ? 'bg-primary-600 text-white'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
              >
                <Plus className="w-4 h-4 inline mr-2" />
                Add Text
              </button>
            </div>

            {/* File Upload */}
            {uploadMode === 'file' && (
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
                  Supports .txt, .md, .pdf, .doc files
                </p>
                <input
                  type="file"
                  multiple
                  onChange={(e) => handleFileSelect(e.target.files)}
                  className="hidden"
                  id="file-upload"
                  accept=".txt,.md,.pdf,.doc,.docx"
                />
                <label
                  htmlFor="file-upload"
                  className="bg-primary-600 text-white px-6 py-2 rounded-lg cursor-pointer hover:bg-primary-700 inline-block"
                >
                  Select Files
                </label>

                {uploadFileMutation.isPending && (
                  <div className="mt-4 flex items-center justify-center gap-2 text-primary-400">
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span>Uploading and vectorizing...</span>
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
                  className="w-full h-64 bg-slate-700 text-white rounded-lg p-4 focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
                <button
                  type="submit"
                  disabled={!textContent.trim() || addTextMutation.isPending}
                  className="bg-primary-600 text-white px-6 py-2 rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {addTextMutation.isPending ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Processing...
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

          {/* Documents List */}
          <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
            <h3 className="text-lg font-semibold text-white mb-4">
              Stored Documents ({documents?.length || 0})
            </h3>

            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
              </div>
            ) : documents && documents.length > 0 ? (
              <div className="space-y-3">
                {documents.map((doc) => (
                  <div
                    key={doc.id}
                    className="bg-slate-700 rounded-lg p-4 hover:bg-slate-600 transition-colors"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <FileText className="w-5 h-5 text-primary-400" />
                          <span className="text-sm text-slate-400">
                            {doc.metadata?.filename || 'Untitled Document'}
                          </span>
                        </div>
                        <p className="text-white text-sm line-clamp-2">
                          {doc.content}
                        </p>
                        <p className="text-xs text-slate-500 mt-2">
                          Added: {new Date(doc.created_at).toLocaleDateString()}
                        </p>
                      </div>
                      <button className="text-red-400 hover:text-red-300 ml-4">
                        <Trash2 className="w-5 h-5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-12 text-slate-400">
                <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>No documents yet. Upload your first document above.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
