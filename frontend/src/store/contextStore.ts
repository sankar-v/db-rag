import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface ContextState {
  selectedConnectionIds: string[]
  selectedDocumentIds: string[]
  toggleConnection: (id: string) => void
  toggleDocument: (id: string) => void
  clearAll: () => void
  setConnections: (ids: string[]) => void
  setDocuments: (ids: string[]) => void
}

export const useContextStore = create<ContextState>()(
  persist(
    (set) => ({
      selectedConnectionIds: [],
      selectedDocumentIds: [],
      
      toggleConnection: (id: string) =>
        set((state) => ({
          selectedConnectionIds: state.selectedConnectionIds.includes(id)
            ? state.selectedConnectionIds.filter((cid) => cid !== id)
            : [...state.selectedConnectionIds, id],
        })),
      
      toggleDocument: (id: string) =>
        set((state) => ({
          selectedDocumentIds: state.selectedDocumentIds.includes(id)
            ? state.selectedDocumentIds.filter((did) => did !== id)
            : [...state.selectedDocumentIds, id],
        })),
      
      clearAll: () =>
        set({
          selectedConnectionIds: [],
          selectedDocumentIds: [],
        }),
      
      setConnections: (ids: string[]) =>
        set({ selectedConnectionIds: ids }),
      
      setDocuments: (ids: string[]) =>
        set({ selectedDocumentIds: ids }),
    }),
    {
      name: 'chat-context-storage',
    }
  )
)
