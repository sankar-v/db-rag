import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import ChatInterface from './pages/ChatInterface'
import DocumentManager from './pages/DocumentManager'
import DatabaseConnections from './pages/DatabaseConnections'
import MetadataExplorer from './pages/MetadataExplorer'

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Navigate to="/chat" replace />} />
          <Route path="/chat" element={<ChatInterface />} />
          <Route path="/documents" element={<DocumentManager />} />
          <Route path="/connections" element={<DatabaseConnections />} />
          <Route path="/metadata" element={<MetadataExplorer />} />
        </Routes>
      </Layout>
    </Router>
  )
}

export default App
