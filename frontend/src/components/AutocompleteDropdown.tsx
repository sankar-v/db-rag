import { useEffect, useRef } from 'react'
import { Clock, Database, Table2, FileText, Sparkles, ChevronRight } from 'lucide-react'
import type { Suggestion } from '../hooks/useAutocomplete'

interface AutocompleteDropdownProps {
  suggestions: Suggestion[]
  selectedIndex: number
  onSelect: (suggestion: Suggestion) => void
  onClose: () => void
  position?: { top: number; left: number; width: number }
}

export default function AutocompleteDropdown({
  suggestions,
  selectedIndex,
  onSelect,
  onClose,
  position,
}: AutocompleteDropdownProps) {
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        onClose()
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [onClose])

  // Scroll selected item into view
  useEffect(() => {
    const selectedElement = dropdownRef.current?.querySelector(`[data-index="${selectedIndex}"]`)
    if (selectedElement) {
      selectedElement.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
    }
  }, [selectedIndex])

  if (suggestions.length === 0) return null

  const getIcon = (type: Suggestion['type']) => {
    switch (type) {
      case 'template':
        return <Sparkles className="w-4 h-4 text-purple-400" />
      case 'table':
        return <Table2 className="w-4 h-4 text-primary-400" />
      case 'column':
        return <Database className="w-4 h-4 text-blue-400" />
      case 'history':
        return <Clock className="w-4 h-4 text-slate-400" />
      case 'ai':
        return <Sparkles className="w-4 h-4 text-green-400" />
      default:
        return <FileText className="w-4 h-4 text-slate-400" />
    }
  }

  const style = position
    ? {
        position: 'absolute' as const,
        top: `${position.top}px`,
        left: `${position.left}px`,
        width: `${position.width}px`,
      }
    : {}

  return (
    <div
      ref={dropdownRef}
      style={style}
      className="bg-slate-800 border border-slate-700 rounded-lg shadow-2xl overflow-hidden z-50 max-h-80 overflow-y-auto"
    >
      {/* Header */}
      <div className="px-3 py-2 bg-slate-900/50 border-b border-slate-700">
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <Sparkles className="w-3 h-3" />
          <span>Suggestions</span>
          <span className="ml-auto text-slate-500">↑↓ navigate • ⏎ select • esc close</span>
        </div>
      </div>

      {/* Suggestions List */}
      <div className="py-1">
        {suggestions.map((suggestion, index) => (
          <button
            key={suggestion.id}
            data-index={index}
            onClick={() => onSelect(suggestion)}
            className={`
              w-full px-3 py-2 flex items-center gap-3 text-left transition-colors
              ${
                index === selectedIndex
                  ? 'bg-primary-600/20 border-l-2 border-primary-500'
                  : 'hover:bg-slate-700/50 border-l-2 border-transparent'
              }
            `}
          >
            {/* Icon */}
            <div className="flex-shrink-0">{getIcon(suggestion.type)}</div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <div className="flex items-baseline gap-2">
                <span
                  className={`text-sm truncate ${
                    index === selectedIndex ? 'text-white font-medium' : 'text-slate-200'
                  }`}
                >
                  {suggestion.text}
                </span>
                {suggestion.category && (
                  <span className="text-xs text-slate-500 flex-shrink-0">
                    {suggestion.category}
                  </span>
                )}
              </div>
              {suggestion.description && (
                <div className="text-xs text-slate-400 truncate mt-0.5">
                  {suggestion.description}
                </div>
              )}
            </div>

            {/* Arrow indicator for selected */}
            {index === selectedIndex && (
              <ChevronRight className="w-4 h-4 text-primary-400 flex-shrink-0" />
            )}
          </button>
        ))}
      </div>

      {/* Footer hint */}
      {suggestions.length > 0 && (
        <div className="px-3 py-2 bg-slate-900/30 border-t border-slate-700 text-xs text-slate-500">
          Showing {suggestions.length} suggestion{suggestions.length !== 1 ? 's' : ''}
        </div>
      )}
    </div>
  )
}
