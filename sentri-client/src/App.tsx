import { Link, useLocation } from 'react-router-dom'
import { ChatWindow } from './components/ChatWindow'
import { ExploreWindow } from './components/ExploreWindow'
import { LayoutDashboard, MessageSquareText } from 'lucide-react'

function Sidebar() {
  const location = useLocation()
  const searchParams = new URLSearchParams(location.search)
  const hasToken = searchParams.has('token')
  
  return (
    <div className="sidebar">
      <div className="sidebar-brand">
        <img src="/logo.png" alt="Sentri Logo" className="brand-logo" />
        <h2>Sentri</h2>
      </div>
      <nav className="sidebar-nav">
        <Link to={`/explore${location.search}`} className={`nav-link ${location.pathname === '/explore' || location.pathname === '/' ? 'active' : ''}`}>
          <LayoutDashboard size={18} />
          <span>Explore Codebase</span>
        </Link>
        
        {/* Disable the RCA tab if there is no token provided in the URL */}
        <Link 
          to={`/incident${location.search}`} 
          className={`nav-link ${location.pathname === '/incident' || location.pathname === '/chat' ? 'active' : ''}`}
          style={{ 
            opacity: hasToken ? 1 : 0.4, 
            pointerEvents: hasToken ? 'auto' : 'none',
            cursor: hasToken ? 'pointer' : 'not-allowed'
          }}
          title={hasToken ? '' : 'Requires a Magic Link token from Slack'}
        >
          <MessageSquareText size={18} />
          <span>Incident RCA</span>
        </Link>
      </nav>
    </div>
  )
}

function App() {
  const location = useLocation()
  
  // Backward compatibility for old magic links pointing to /chat
  const isIncidentRoute = location.pathname === '/incident' || location.pathname === '/chat'
  const isExploreRoute = location.pathname === '/' || location.pathname === '/explore'
  
  return (
    <div className="app-layout">
      <Sidebar />
      <main className="main-content">
        {/* Render both windows but toggle visibility to preserve their internal states */}
        <div style={{ display: isExploreRoute ? 'block' : 'none', height: '100%' }}>
          <ExploreWindow />
        </div>
        <div style={{ display: isIncidentRoute ? 'block' : 'none', height: '100%' }}>
          <ChatWindow />
        </div>
      </main>
    </div>
  )
}

export default App
