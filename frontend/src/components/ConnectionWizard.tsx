import { useState, useEffect } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { 
  Database, 
  Check, 
  X, 
  Loader2, 
  ChevronRight, 
  ChevronLeft,
  AlertCircle,
  CheckCircle2
} from 'lucide-react'
import { connectionAPI } from '../api/client'

interface ConnectionWizardProps {
  onComplete: (connectionId: string) => void
  onCancel: () => void
  editConnection?: any
}

interface ConnectionFormData {
  name: string
  host: string
  port: number
  database: string
  user: string
  password: string
  schema: string
}

interface TableInfo {
  table_name: string
  schema: string
  selected: boolean
}

export default function ConnectionWizard({ onComplete, onCancel, editConnection }: ConnectionWizardProps) {
  const [currentStep, setCurrentStep] = useState(1)
  const [formData, setFormData] = useState<ConnectionFormData>({
    name: editConnection?.name || '',
    host: editConnection?.host || 'localhost',
    port: editConnection?.port || 5432,
    database: editConnection?.database || '',
    user: editConnection?.user || '',
    password: editConnection?.password || '',
    schema: editConnection?.schema || 'public',
  })
  const [testResult, setTestResult] = useState<any>(null)
  const [availableTables, setAvailableTables] = useState<TableInfo[]>([])
  const [syncProgress, setSyncProgress] = useState<any>(null)
  const [connectionId, setConnectionId] = useState<string | null>(null)

  // Test connection mutation
  const testMutation = useMutation({
    mutationFn: connectionAPI.test,
    onSuccess: (data) => {
      setTestResult(data)
      if (data.success && data.tables) {
        // Select ALL tables by default
        setAvailableTables(
          data.tables.map((table: string) => ({
            table_name: table,
            schema: formData.schema,
            selected: true,  // All tables selected by default
          }))
        )
      }
    },
  })

  // Save connection mutation
  const saveMutation = useMutation({
    mutationFn: connectionAPI.save,
    onSuccess: (data) => {
      setConnectionId(data.connection_id)
    },
  })

  // Sync metadata mutation
  const syncMutation = useMutation({
    mutationFn: ({ connectionId, tables }: { connectionId: string; tables: string[] }) =>
      connectionAPI.syncTables(connectionId, tables),
    onSuccess: (data) => {
      setSyncProgress(data)
    },
  })

  const handleNext = async () => {
    if (currentStep === 1) {
      // Validate form data
      if (!formData.name || !formData.host || !formData.database || !formData.user) {
        return
      }
      setCurrentStep(2)
    } else if (currentStep === 2) {
      // Test connection
      testMutation.mutate(formData)
    } else if (currentStep === 3) {
      // Save connection
      const selectedTables = availableTables.filter((t) => t.selected).map((t) => t.table_name)
      const saveData = { ...formData, tables: selectedTables }
      saveMutation.mutate(saveData)
      setCurrentStep(4)
    } else if (currentStep === 4 && connectionId) {
      // Start metadata sync
      const selectedTables = availableTables.filter((t) => t.selected).map((t) => t.table_name)
      syncMutation.mutate({ connectionId, tables: selectedTables })
    } else if (currentStep === 5) {
      // Complete wizard
      if (connectionId) {
        onComplete(connectionId)
      }
    }
  }

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1)
    }
  }

  const toggleTableSelection = (tableName: string) => {
    setAvailableTables((prev) =>
      prev.map((t) => (t.table_name === tableName ? { ...t, selected: !t.selected } : t))
    )
  }

  const toggleAllTables = () => {
    const allSelected = availableTables.every((t) => t.selected)
    setAvailableTables((prev) => prev.map((t) => ({ ...t, selected: !allSelected })))
  }

  // Auto-advance on successful test
  useEffect(() => {
    if (testResult?.success && currentStep === 2) {
      setCurrentStep(3)
    }
  }, [testResult, currentStep])

  // Auto-advance on successful save
  useEffect(() => {
    if (connectionId && currentStep === 4) {
      const selectedTables = availableTables.filter((t) => t.selected).map((t) => t.table_name)
      syncMutation.mutate({ connectionId, tables: selectedTables })
      setCurrentStep(5)
    }
  }, [connectionId, currentStep])

  const steps = [
    { number: 1, name: 'Connection Details' },
    { number: 2, name: 'Test Connection' },
    { number: 3, name: 'Select Tables' },
    { number: 4, name: 'Sync Metadata' },
    { number: 5, name: 'Complete' },
  ]

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-slate-800 rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-slate-700">
          <h2 className="text-2xl font-bold text-white flex items-center gap-3">
            <Database className="w-7 h-7 text-primary-500" />
            {editConnection ? 'Edit Connection' : 'New Database Connection'}
          </h2>
          
          {/* Progress Steps */}
          <div className="mt-6 flex items-center justify-between">
            {steps.map((step, idx) => (
              <div key={step.number} className="flex items-center flex-1">
                <div className="flex flex-col items-center flex-1">
                  <div
                    className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold ${
                      currentStep >= step.number
                        ? 'bg-primary-600 text-white'
                        : 'bg-slate-700 text-slate-400'
                    }`}
                  >
                    {currentStep > step.number ? (
                      <Check className="w-5 h-5" />
                    ) : (
                      step.number
                    )}
                  </div>
                  <span
                    className={`text-xs mt-2 text-center ${
                      currentStep >= step.number ? 'text-white' : 'text-slate-400'
                    }`}
                  >
                    {step.name}
                  </span>
                </div>
                {idx < steps.length - 1 && (
                  <div
                    className={`h-0.5 flex-1 -mt-6 ${
                      currentStep > step.number ? 'bg-primary-600' : 'bg-slate-700'
                    }`}
                  />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          {/* Step 1: Connection Details */}
          {currentStep === 1 && (
            <div className="space-y-4 max-w-2xl mx-auto">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Connection Name *
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="My Production Database"
                  className="w-full bg-slate-700 text-white rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Host *
                  </label>
                  <input
                    type="text"
                    value={formData.host}
                    onChange={(e) => setFormData({ ...formData, host: e.target.value })}
                    placeholder="localhost"
                    className="w-full bg-slate-700 text-white rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Port *
                  </label>
                  <input
                    type="number"
                    value={formData.port}
                    onChange={(e) => setFormData({ ...formData, port: parseInt(e.target.value) })}
                    placeholder="5432"
                    className="w-full bg-slate-700 text-white rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Database Name *
                </label>
                <input
                  type="text"
                  value={formData.database}
                  onChange={(e) => setFormData({ ...formData, database: e.target.value })}
                  placeholder="mydb"
                  className="w-full bg-slate-700 text-white rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Username *
                  </label>
                  <input
                    type="text"
                    value={formData.user}
                    onChange={(e) => setFormData({ ...formData, user: e.target.value })}
                    placeholder="postgres"
                    className="w-full bg-slate-700 text-white rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Password *
                  </label>
                  <input
                    type="password"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    placeholder="••••••••"
                    className="w-full bg-slate-700 text-white rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Schema
                </label>
                <input
                  type="text"
                  value={formData.schema}
                  onChange={(e) => setFormData({ ...formData, schema: e.target.value })}
                  placeholder="public"
                  className="w-full bg-slate-700 text-white rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>
            </div>
          )}

          {/* Step 2: Test Connection */}
          {currentStep === 2 && (
            <div className="flex flex-col items-center justify-center py-12">
              {!testResult ? (
                <>
                  <Loader2 className="w-16 h-16 text-primary-500 animate-spin mb-4" />
                  <p className="text-slate-300 text-lg">Testing connection...</p>
                  <p className="text-slate-400 text-sm mt-2">
                    Connecting to {formData.host}:{formData.port}/{formData.database}
                  </p>
                </>
              ) : testResult.success ? (
                <>
                  <CheckCircle2 className="w-16 h-16 text-green-500 mb-4" />
                  <p className="text-white text-lg font-semibold">Connection Successful!</p>
                  <p className="text-slate-400 text-sm mt-2">
                    Found {testResult.tables?.length || 0} tables
                  </p>
                </>
              ) : (
                <>
                  <AlertCircle className="w-16 h-16 text-red-500 mb-4" />
                  <p className="text-white text-lg font-semibold">Connection Failed</p>
                  <p className="text-red-400 text-sm mt-2">{testResult.error}</p>
                  <button
                    onClick={() => testMutation.mutate(formData)}
                    className="mt-4 bg-primary-600 text-white px-6 py-2 rounded-lg hover:bg-primary-700"
                  >
                    Retry
                  </button>
                </>
              )}
            </div>
          )}

          {/* Step 3: Select Tables */}
          {currentStep === 3 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-white">
                  Select Tables to Sync ({availableTables.filter((t) => t.selected).length}/
                  {availableTables.length})
                </h3>
                <button
                  onClick={toggleAllTables}
                  className="text-primary-500 hover:text-primary-400 text-sm font-medium"
                >
                  {availableTables.every((t) => t.selected) ? 'Deselect All' : 'Select All'}
                </button>
              </div>

              <div className="bg-slate-700 rounded-lg max-h-96 overflow-auto">
                {availableTables.map((table) => (
                  <label
                    key={table.table_name}
                    className="flex items-center gap-3 p-3 hover:bg-slate-600 cursor-pointer border-b border-slate-600 last:border-0"
                  >
                    <input
                      type="checkbox"
                      checked={table.selected}
                      onChange={() => toggleTableSelection(table.table_name)}
                      className="w-5 h-5 text-primary-600 bg-slate-600 border-slate-500 rounded focus:ring-primary-500"
                    />
                    <Database className="w-4 h-4 text-slate-400" />
                    <span className="text-white">{table.table_name}</span>
                  </label>
                ))}
              </div>
            </div>
          )}

          {/* Step 4: Saving */}
          {currentStep === 4 && (
            <div className="flex flex-col items-center justify-center py-12">
              <Loader2 className="w-16 h-16 text-primary-500 animate-spin mb-4" />
              <p className="text-slate-300 text-lg">Saving connection...</p>
            </div>
          )}

          {/* Step 5: Sync Progress & Complete */}
          {currentStep === 5 && (
            <div className="space-y-6">
              {syncMutation.isPending ? (
                <div className="flex flex-col items-center justify-center py-12">
                  <Loader2 className="w-16 h-16 text-primary-500 animate-spin mb-4" />
                  <p className="text-slate-300 text-lg">Syncing metadata...</p>
                  <p className="text-slate-400 text-sm mt-2">
                    This may take a few moments
                  </p>
                </div>
              ) : syncProgress ? (
                <div className="space-y-4">
                  <div className="flex flex-col items-center py-8">
                    <CheckCircle2 className="w-20 h-20 text-green-500 mb-4" />
                    <h3 className="text-2xl font-bold text-white mb-2">Setup Complete!</h3>
                    <p className="text-slate-400 text-center">
                      Your database connection is ready to use
                    </p>
                  </div>

                  <div className="bg-slate-700 rounded-lg p-6 space-y-3">
                    <h4 className="font-semibold text-white mb-4">Connection Summary</h4>
                    
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-slate-400">Name:</span>
                        <span className="text-white ml-2 font-medium">{formData.name}</span>
                      </div>
                      <div>
                        <span className="text-slate-400">Host:</span>
                        <span className="text-white ml-2 font-medium">{formData.host}:{formData.port}</span>
                      </div>
                      <div>
                        <span className="text-slate-400">Database:</span>
                        <span className="text-white ml-2 font-medium">{formData.database}</span>
                      </div>
                      <div>
                        <span className="text-slate-400">Schema:</span>
                        <span className="text-white ml-2 font-medium">{formData.schema}</span>
                      </div>
                      <div className="col-span-2">
                        <span className="text-slate-400">Tables Synced:</span>
                        <span className="text-white ml-2 font-medium">
                          {syncProgress.tables_synced || availableTables.filter((t) => t.selected).length}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              ) : null}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-slate-700 flex items-center justify-between">
          <button
            onClick={onCancel}
            className="text-slate-400 hover:text-white px-4 py-2"
          >
            Cancel
          </button>

          <div className="flex items-center gap-3">
            {currentStep > 1 && currentStep < 5 && (
              <button
                onClick={handleBack}
                disabled={testMutation.isPending || saveMutation.isPending || syncMutation.isPending}
                className="bg-slate-700 text-white px-6 py-2 rounded-lg hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                <ChevronLeft className="w-4 h-4" />
                Back
              </button>
            )}

            {currentStep < 5 ? (
              <button
                onClick={handleNext}
                disabled={
                  testMutation.isPending ||
                  saveMutation.isPending ||
                  syncMutation.isPending ||
                  (currentStep === 3 && availableTables.filter((t) => t.selected).length === 0) ||
                  (currentStep === 1 && (!formData.name || !formData.host || !formData.database || !formData.user))
                }
                className="bg-primary-600 text-white px-6 py-2 rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {currentStep === 2 ? 'Test Connection' : 'Next'}
                <ChevronRight className="w-4 h-4" />
              </button>
            ) : (
              <button
                onClick={handleNext}
                className="bg-green-600 text-white px-8 py-2 rounded-lg hover:bg-green-700 flex items-center gap-2"
              >
                <Check className="w-5 h-5" />
                Finish
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
