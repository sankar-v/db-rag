import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Types
export interface QueryRequest {
  question: string
  mode?: 'auto' | 'sql' | 'vector'
}

export interface QueryResponse {
  success: boolean
  answer: string
  query: string
  sql_results?: any
  vector_results?: any
  routing?: any[]
  error?: string
}

export interface SystemStatus {
  status: string
  database_connected: boolean
  tables_count: number
  documents_count: number
  metadata_synced: boolean
}

export interface Document {
  id: string
  content: string
  metadata: any
  created_at: string
}

export interface Table {
  table_name: string
  schema: string
}

export interface TableMetadata {
  table_name: string
  description: string
  columns: any[]
  sample_data: any[]
}

export interface SuggestionItem {
  text: string
  type: 'completion' | 'refinement' | 'template'
  confidence: number
  description?: string
}

export interface SuggestionsResponse {
  suggestions: SuggestionItem[]
}

// API functions
export const queryAPI = {
  query: async (request: QueryRequest): Promise<QueryResponse> => {
    const response = await api.post('/api/query', request)
    return response.data
  },

  getStatus: async (): Promise<SystemStatus> => {
    const response = await api.get('/api/status')
    return response.data
  },

  getSuggestions: async (partialQuery: string, context?: any): Promise<SuggestionsResponse> => {
    const response = await api.post('/api/query/suggestions', {
      partial_query: partialQuery,
      context,
    })
    return response.data
  },
}

export const documentAPI = {
  list: async (limit = 10, offset = 0): Promise<Document[]> => {
    const response = await api.get('/api/documents', { params: { limit, offset } })
    return response.data.documents
  },

  add: async (content: string, metadata?: any): Promise<string> => {
    const response = await api.post('/api/documents', { content, metadata })
    return response.data.document_id
  },

  upload: async (file: File): Promise<string> => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await api.post('/api/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data.document_id
  },
}

export const metadataAPI = {
  listTables: async (): Promise<Table[]> => {
    const response = await api.get('/api/tables')
    return response.data.tables
  },

  getTableMetadata: async (tableName: string): Promise<TableMetadata> => {
    const response = await api.get(`/api/tables/${tableName}`)
    return response.data.metadata
  },

  syncMetadata: async (forceUpdate = false): Promise<void> => {
    await api.post('/api/metadata/sync', null, { params: { force_update: forceUpdate } })
  },
}

// Deprecated: Use metadataAPI instead
export const tableAPI = {
  list: async (): Promise<Table[]> => {
    return metadataAPI.listTables()
  },

  getMetadata: async (tableName: string): Promise<TableMetadata> => {
    return metadataAPI.getTableMetadata(tableName)
  },

  syncMetadata: async (forceUpdate = false): Promise<void> => {
    return metadataAPI.syncMetadata(forceUpdate)
  },
}

export const connectionAPI = {
  list: async (): Promise<any[]> => {
    const response = await api.get('/api/connections')
    return response.data.connections
  },

  test: async (config: any): Promise<{ success: boolean; message?: string; error?: string; tables?: string[] }> => {
    const response = await api.post('/api/connections/test', config)
    return response.data
  },

  save: async (config: any): Promise<{ success: boolean; connection_id: string; message: string }> => {
    const response = await api.post('/api/connections', config)
    return response.data
  },

  update: async (id: string, config: any): Promise<{ success: boolean; message: string }> => {
    const response = await api.put(`/api/connections/${id}`, config)
    return response.data
  },

  delete: async (id: string): Promise<{ success: boolean; message: string }> => {
    const response = await api.delete(`/api/connections/${id}`)
    return response.data
  },

  setActive: async (id: string): Promise<{ success: boolean; message: string }> => {
    const response = await api.post(`/api/connections/${id}/activate`)
    return response.data
  },

  syncTables: async (connectionId: string, tables: string[]): Promise<{ success: boolean; tables_synced: number }> => {
    const response = await api.post(`/api/connections/${connectionId}/sync`, { tables })
    return response.data
  },

  // Legacy methods for backwards compatibility
  configure: async (config: any): Promise<{ success: boolean; message: string }> => {
    const response = await api.post('/api/connection/configure', config)
    return response.data
  },
}
