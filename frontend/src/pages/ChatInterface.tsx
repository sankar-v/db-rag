import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { Send, Loader2, Database, FileText, AlertCircle, MessageSquare } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { queryAPI } from '../api/client'
import ActiveContext from '../components/ActiveContext'
import AutocompleteDropdown from '../components/AutocompleteDropdown'
import { useAutocomplete } from '../hooks/useAutocomplete'
import type { Suggestion } from '../hooks/useAutocomplete'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  metadata?: {
    sql_results?: any
    vector_results?: any
    routing?: any[]
  }
  timestamp: Date
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [queryMode, setQueryMode] = useState<'auto' | 'sql' | 'vector'>('auto')
  const [showAutocomplete, setShowAutocomplete] = useState(false)
  const [selectedSuggestionIndex, setSelectedSuggestionIndex] = useState(0)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const inputContainerRef = useRef<HTMLDivElement>(null)

  // Autocomplete
  const { suggestions, isLoading: isSuggestionsLoading, saveToHistory } = useAutocomplete(
    input,
    showAutocomplete
  )

  // Get system status
  const { data: status } = useQuery({
    queryKey: ['system-status'],
    queryFn: queryAPI.getStatus,
    refetchInterval: 10000, // Refresh every 10 seconds
  })

  // Query mutation
  const queryMutation = useMutation({
    mutationFn: queryAPI.query,
    onSuccess: (data) => {
      const assistantMessage: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: data.answer,
        metadata: {
          sql_results: data.sql_results,
          vector_results: data.vector_results,
          routing: data.routing,
        },
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, assistantMessage])
    },
    onError: (error) => {
      const errorMessage: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: `Error: ${error.message}`,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, errorMessage])
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || queryMutation.isPending) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    queryMutation.mutate({ question: input, mode: queryMode })
    saveToHistory(input) // Save to query history
    setInput('')
    setShowAutocomplete(false)
  }

  // Handle suggestion selection
  const handleSelectSuggestion = (suggestion: Suggestion) => {
    const textToInsert = suggestion.insertText || suggestion.text
    
    // Smart insertion based on suggestion type
    if (suggestion.type === 'table' || suggestion.type === 'column') {
      // For tables/columns, intelligently insert at cursor or append
      const currentInput = input.trim()
      
      // If input ends with preposition or incomplete phrase, append
      if (currentInput.match(/(from|join|in|table|into|where|and|or)$/i)) {
        setInput(`${currentInput} ${textToInsert}`)
      } 
      // If input contains the table mention already, replace just that word
      else if (currentInput.toLowerCase().includes(textToInsert.toLowerCase())) {
        setInput(currentInput)
      }
      // Otherwise, intelligently insert
      else {
        // Check if we're in the middle of a query template
        const templates = ['Show me', 'What', 'Count', 'Find', 'List', 'How many']
        const startsWithTemplate = templates.some(t => currentInput.startsWith(t))
        
        if (startsWithTemplate) {
          // Append to the query
          setInput(`${currentInput} ${textToInsert}`)
        } else {
          // Start fresh with a template
          setInput(`Show me data from ${textToInsert}`)
        }
      }
    } else if (suggestion.type === 'template') {
      // For templates, replace or use as-is
      setInput(textToInsert)
    } else if (suggestion.type === 'history') {
      // For history, replace entirely
      setInput(textToInsert)
    } else {
      // Default behavior
      setInput(textToInsert)
    }
    
    setShowAutocomplete(false)
    inputRef.current?.focus()
  }

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!showAutocomplete || suggestions.length === 0) {
      // Show autocomplete on key press if not visible
      if (e.key !== 'Enter' && e.key !== 'Escape') {
        setShowAutocomplete(true)
      }
      return
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setSelectedSuggestionIndex((prev) => 
          prev < suggestions.length - 1 ? prev + 1 : prev
        )
        break
      case 'ArrowUp':
        e.preventDefault()
        setSelectedSuggestionIndex((prev) => (prev > 0 ? prev - 1 : 0))
        break
      case 'Enter':
        if (suggestions[selectedSuggestionIndex]) {
          e.preventDefault()
          handleSelectSuggestion(suggestions[selectedSuggestionIndex])
        }
        break
      case 'Escape':
        e.preventDefault()
        setShowAutocomplete(false)
        setSelectedSuggestionIndex(0)
        break
      case 'Tab':
        if (suggestions[selectedSuggestionIndex]) {
          e.preventDefault()
          handleSelectSuggestion(suggestions[selectedSuggestionIndex])
        }
        break
    }
  }

  // Reset selection index when suggestions change
  useEffect(() => {
    setSelectedSuggestionIndex(0)
  }, [suggestions])

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="flex flex-col h-full bg-slate-900">
      {/* Header */}
      <div className="bg-slate-800 border-b border-slate-700 p-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-white">Conversational Database Query</h2>
            <p className="text-sm text-slate-400 mt-1">
              Ask questions in natural language
            </p>
          </div>

          {/* System Status */}
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${status?.database_connected ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-sm text-slate-400">
              {status?.database_connected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>

        {/* Query Mode Selector */}
        <div className="flex gap-2 mt-4">
          <button
            onClick={() => setQueryMode('auto')}
            className={`px-3 py-1 rounded text-sm ${
              queryMode === 'auto'
                ? 'bg-primary-600 text-white'
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            Auto
          </button>
          <button
            onClick={() => setQueryMode('sql')}
            className={`px-3 py-1 rounded text-sm flex items-center gap-1 ${
              queryMode === 'sql'
                ? 'bg-primary-600 text-white'
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            <Database className="w-3 h-3" />
            SQL Only
          </button>
          <button
            onClick={() => setQueryMode('vector')}
            className={`px-3 py-1 rounded text-sm flex items-center gap-1 ${
              queryMode === 'vector'
                ? 'bg-primary-600 text-white'
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            <FileText className="w-3 h-3" />
            Vector Only
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-auto p-6 space-y-6">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-400">
            <MessageSquare className="w-16 h-16 mb-4 opacity-50" />
            <h3 className="text-lg font-medium mb-2">Start a conversation</h3>
            <p className="text-sm text-center max-w-md">
              Ask questions about your database or search through documents.
              The system will intelligently route your query to the right agent.
            </p>
            <div className="mt-6 space-y-2">
              <div className="text-sm bg-slate-800 rounded px-3 py-2">
                "How many customers do we have?"
              </div>
              <div className="text-sm bg-slate-800 rounded px-3 py-2">
                "What are the top 5 rented films?"
              </div>
              <div className="text-sm bg-slate-800 rounded px-3 py-2">
                "What is our vacation policy?"
              </div>
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'} animate-fade-in`}
            >
              <div
                className={`max-w-3xl rounded-lg p-4 ${
                  message.role === 'user'
                    ? 'bg-primary-600 text-white'
                    : 'bg-slate-800 text-slate-100'
                }`}
              >
                <div className="prose prose-invert max-w-none">
                  <ReactMarkdown
                    components={{
                      code({ className, children }) {
                        const match = /language-(\w+)/.exec(className || '')
                        const inline = !className
                        return !inline && match ? (
                          <SyntaxHighlighter
                            style={vscDarkPlus as any}
                            language={match[1]}
                            PreTag="div"
                          >
                            {String(children).replace(/\n$/, '')}
                          </SyntaxHighlighter>
                        ) : (
                          <code className={className}>
                            {children}
                          </code>
                        )
                      },
                    }}
                  >
                    {message.content}
                  </ReactMarkdown>
                </div>

                {/* Metadata */}
                {message.metadata?.routing && (
                  <div className="mt-3 pt-3 border-t border-slate-700">
                    <div className="text-xs text-slate-400">
                      Routed to: {message.metadata.routing.map(r => r.agent).join(', ')}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))
        )}

        {/* Loading indicator */}
        {queryMutation.isPending && (
          <div className="flex justify-start animate-fade-in">
            <div className="bg-slate-800 rounded-lg p-4">
              <Loader2 className="w-5 h-5 text-primary-500 animate-spin" />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-slate-700 p-4 bg-slate-800">
        {!status?.database_connected && (
          <div className="mb-3 p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg flex items-center gap-2 text-sm text-amber-400">
            <AlertCircle className="w-4 h-4" />
            Database not connected. Please configure connection in Settings.
          </div>
        )}

        {/* Active Context Component */}
        <ActiveContext />
        
        <form onSubmit={handleSubmit} className="flex gap-3 relative">
          <div ref={inputContainerRef} className="flex-1 relative">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => {
                setInput(e.target.value)
                setShowAutocomplete(true)
              }}
              onKeyDown={handleKeyDown}
              onFocus={() => setShowAutocomplete(true)}
              placeholder="Ask a question..."
              disabled={queryMutation.isPending || !status?.database_connected}
              className="w-full bg-slate-700 text-white rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
            />
            
            {/* Autocomplete Dropdown */}
            {showAutocomplete && suggestions.length > 0 && inputContainerRef.current && (
              <div className="absolute bottom-full left-0 right-0 mb-2 z-50">
                <AutocompleteDropdown
                  suggestions={suggestions}
                  selectedIndex={selectedSuggestionIndex}
                  onSelect={handleSelectSuggestion}
                  onClose={() => {
                    setShowAutocomplete(false)
                    setSelectedSuggestionIndex(0)
                  }}
                  position={undefined}
                />
              </div>
            )}
          </div>
          
          <button
            type="submit"
            disabled={queryMutation.isPending || !input.trim() || !status?.database_connected}
            className="bg-primary-600 text-white px-6 py-3 rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-colors"
          >
            {queryMutation.isPending ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </form>
      </div>
    </div>
  )
}
