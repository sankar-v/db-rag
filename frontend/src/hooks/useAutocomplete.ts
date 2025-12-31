import { useState, useEffect, useCallback, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { metadataAPI, connectionAPI, queryAPI } from '../api/client'
import { useContextStore } from '../store/contextStore'

export interface Suggestion {
  id: string
  text: string
  type: 'template' | 'table' | 'column' | 'history' | 'ai'
  category?: string
  description?: string
  insertText?: string // What actually gets inserted (may differ from display text)
}

// Query templates categorized by intent
const QUERY_TEMPLATES: Suggestion[] = [
  // Data exploration - keep cursor position friendly
  { id: 't1', text: 'Show me all records from', type: 'template', category: 'Exploration', description: 'Browse table data' },
  { id: 't2', text: 'What columns are in', type: 'template', category: 'Schema', description: 'View table structure' },
  { id: 't3', text: 'Count the number of rows in', type: 'template', category: 'Analysis', description: 'Get row count' },
  { id: 't4', text: 'Show me the first 10 rows from', type: 'template', category: 'Exploration', description: 'Preview data' },
  
  // Filtering & Search
  { id: 't5', text: 'Find all', type: 'template', category: 'Search', description: 'Filter records' },
  { id: 't6', text: 'Show me records where', type: 'template', category: 'Search', description: 'Conditional query' },
  { id: 't7', text: 'Search for', type: 'template', category: 'Search', description: 'Text search' },
  { id: 't8', text: 'List all', type: 'template', category: 'Exploration', description: 'View all items' },
  
  // Aggregations
  { id: 't9', text: 'What is the average', type: 'template', category: 'Analysis', description: 'Calculate average' },
  { id: 't10', text: 'Sum of', type: 'template', category: 'Analysis', description: 'Calculate total' },
  { id: 't11', text: 'Group by', type: 'template', category: 'Analysis', description: 'Aggregate data' },
  { id: 't12', text: 'Count distinct', type: 'template', category: 'Analysis', description: 'Unique values' },
  { id: 't13', text: 'How many', type: 'template', category: 'Analysis', description: 'Count items' },
  
  // Relationships
  { id: 't14', text: 'Join', type: 'template', category: 'Relations', description: 'Combine tables' },
  { id: 't15', text: 'Show me relationships between', type: 'template', category: 'Relations', description: 'Find connections' },
  
  // Time-based
  { id: 't16', text: 'Show me data from the last', type: 'template', category: 'Time', description: 'Recent data' },
  { id: 't17', text: 'Compare data between', type: 'template', category: 'Analysis', description: 'Period comparison' },
  
  // Sorting
  { id: 't18', text: 'Top 10', type: 'template', category: 'Analysis', description: 'Highest values' },
  { id: 't19', text: 'Sort by', type: 'template', category: 'Exploration', description: 'Order results' },
]

const RECENT_QUERIES_KEY = 'db-rag-query-history'
const MAX_HISTORY = 20

export function useAutocomplete(input: string, isEnabled: boolean = true) {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const debounceTimer = useRef<NodeJS.Timeout>()
  const aiDebounceTimer = useRef<NodeJS.Timeout>()
  const { selectedConnectionIds } = useContextStore()

  // Fetch tables for schema-aware suggestions
  const { data: tables } = useQuery({
    queryKey: ['tables'],
    queryFn: metadataAPI.listTables,
    enabled: isEnabled,
    staleTime: 30000, // Cache for 30 seconds
  })

  // Fetch connections for context
  const { data: connections } = useQuery({
    queryKey: ['connections'],
    queryFn: connectionAPI.list,
    enabled: isEnabled,
    staleTime: 30000,
  })

  // Cache for table metadata (columns)
  const [tableMetadataCache, setTableMetadataCache] = useState<Record<string, any>>({})
  const fetchingTables = useRef<Set<string>>(new Set())

  // Get query history from localStorage
  const getQueryHistory = useCallback((): Suggestion[] => {
    try {
      const history = JSON.parse(localStorage.getItem(RECENT_QUERIES_KEY) || '[]')
      return history.slice(0, 10).map((query: string, idx: number) => ({
        id: `h${idx}`,
        text: query,
        type: 'history' as const,
        category: 'Recent',
        description: 'Recent query',
      }))
    } catch {
      return []
    }
  }, [])

  // Save query to history
  const saveToHistory = useCallback((query: string) => {
    if (!query.trim()) return
    
    try {
      const history = JSON.parse(localStorage.getItem(RECENT_QUERIES_KEY) || '[]')
      const updated = [query, ...history.filter((q: string) => q !== query)].slice(0, MAX_HISTORY)
      localStorage.setItem(RECENT_QUERIES_KEY, JSON.stringify(updated))
    } catch (error) {
      console.error('Failed to save query history:', error)
    }
  }, [])

  // Generate suggestions based on input
  const generateSuggestions = useCallback(async () => {
    if (!input.trim()) {
      // No input - show templates and recent queries
      const history = getQueryHistory()
      
      // Also show top 5 table names for quick access
      const topTables = (tables || []).slice(0, 8).map(t => ({
        id: `table-${t.table_name}`,
        text: t.table_name,
        type: 'table' as const,
        category: 'Tables',
        description: `Query the ${t.table_name} table`,
        insertText: `Show me data from ${t.table_name}`,
      }))
      
      setSuggestions([...history.slice(0, 3), ...topTables, ...QUERY_TEMPLATES.slice(0, 5)])
      return
    }

    const lowerInput = input.toLowerCase()
    const results: Suggestion[] = []

    // PRIORITY 1: Match table names (show these first!)
    if (tables && tables.length > 0) {
      const matchedTables = tables
        .filter(t => 
          t.table_name.toLowerCase().includes(lowerInput) ||
          lowerInput.includes(t.table_name.toLowerCase())
        )
        .map(t => ({
          id: `table-${t.table_name}`,
          text: t.table_name,
          type: 'table' as const,
          category: t.schema || 'Table',
          description: `Table with data about ${t.table_name}`,
          insertText: t.table_name,
        }))
      results.push(...matchedTables.slice(0, 5))
    }

    // PRIORITY 2: Detect if user mentioned a table - show its columns
    if (tables && tables.length > 0) {
      const words = input.toLowerCase().split(/\s+/)
      const mentionedTables = tables.filter(t => 
        words.some(w => w === t.table_name.toLowerCase() || w.includes(t.table_name.toLowerCase()))
      )
      
      // Fetch column metadata for mentioned tables
      for (const table of mentionedTables.slice(0, 2)) { // Limit to 2 tables
        if (!tableMetadataCache[table.table_name] && !fetchingTables.current.has(table.table_name)) {
          fetchingTables.current.add(table.table_name)
          try {
            const metadata = await metadataAPI.getTableMetadata(table.table_name)
            setTableMetadataCache(prev => ({ ...prev, [table.table_name]: metadata }))
          } catch (error) {
            console.error(`Failed to fetch metadata for ${table.table_name}:`, error)
          } finally {
            fetchingTables.current.delete(table.table_name)
          }
        }
        
        // If we have cached metadata, suggest columns
        const metadata = tableMetadataCache[table.table_name]
        if (metadata?.columns) {
          const columnSuggestions = metadata.columns
            .slice(0, 5)
            .map((col: any, idx: number) => ({
              id: `col-${table.table_name}-${col.column_name || col.name}-${idx}`,
              text: col.column_name || col.name,
              type: 'column' as const,
              category: `${table.table_name} column`,
              description: col.data_type ? `${col.data_type} column` : 'Table column',
              insertText: col.column_name || col.name,
            }))
          results.push(...columnSuggestions)
        }
      }
    }

    // PRIORITY 3: Match query templates
    const matchedTemplates = QUERY_TEMPLATES.filter(t => 
      t.text.toLowerCase().includes(lowerInput) ||
      t.description?.toLowerCase().includes(lowerInput) ||
      t.category?.toLowerCase().includes(lowerInput)
    )
    results.push(...matchedTemplates.slice(0, 3))

    // PRIORITY 4: Match query history
    const history = getQueryHistory()
    const matchedHistory = history.filter(h => 
      h.text.toLowerCase().includes(lowerInput)
    )
    results.push(...matchedHistory.slice(0, 2))

    // Deduplicate and limit
    const uniqueSuggestions = results.filter((item, index, self) =>
      index === self.findIndex(t => t.text.toLowerCase() === item.text.toLowerCase())
    ).slice(0, 10)

    setSuggestions(uniqueSuggestions)
  }, [input, tables, getQueryHistory, tableMetadataCache])

  // Fetch AI suggestions for longer queries
  const fetchAISuggestions = useCallback(async () => {
    if (!input || input.length < 5) return // Only for meaningful input
    
    try {
      const response = await queryAPI.getSuggestions(input, {
        selectedConnectionIds,
      })
      
      // Convert AI suggestions and merge with existing
      const aiSuggestions: Suggestion[] = response.suggestions.map((s, idx) => ({
        id: `ai-${idx}`,
        text: s.text,
        type: 'ai' as const,
        category: 'AI Suggested',
        description: s.description,
      }))
      
      // Merge AI suggestions with existing (prioritize AI suggestions)
      setSuggestions(prev => {
        const combined = [...aiSuggestions, ...prev]
        // Deduplicate
        const unique = combined.filter((item, index, self) =>
          index === self.findIndex(t => t.text.toLowerCase() === item.text.toLowerCase())
        )
        return unique.slice(0, 10)
      })
    } catch (error) {
      console.error('Failed to fetch AI suggestions:', error)
    }
  }, [input, selectedConnectionIds])

  // Debounced suggestion generation
  useEffect(() => {
    if (!isEnabled) {
      setSuggestions([])
      return
    }

    // Clear previous timer
    if (debounceTimer.current) {
      clearTimeout(debounceTimer.current)
    }

    // Immediate suggestions for empty input
    if (input.length === 0) {
      generateSuggestions()
      return
    }

    // Debounce for longer input
    setIsLoading(true)
    debounceTimer.current = setTimeout(() => {
      generateSuggestions().finally(() => setIsLoading(false))
    }, 100) // Reduced to 100ms for faster response

    // Longer debounce for AI suggestions (reduce API calls)
    if (input.length >= 5) {
      if (aiDebounceTimer.current) {
        clearTimeout(aiDebounceTimer.current)
      }
      
      aiDebounceTimer.current = setTimeout(() => {
        fetchAISuggestions()
      }, 800) // 800ms debounce for AI
    }

    return () => {
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current)
      }
      if (aiDebounceTimer.current) {
        clearTimeout(aiDebounceTimer.current)
      }
    }
  }, [input, isEnabled, generateSuggestions, fetchAISuggestions])

  return {
    suggestions,
    isLoading,
    saveToHistory,
  }
}
