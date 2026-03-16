import { ChatInterface } from './components/ChatInterface'
import './App.css'

function App() {
  return (
    <div className="app">
      {/* Header */}
      <header className="app-header">
        <div className="logo">
          رحلت<span>ك</span> ✈️
        </div>
      </header>

      {/* Main Full Page Chat */}
      <main className="app-main-full">
        <ChatInterface />
      </main>

      {/* Footer */}
      <footer className="app-footer">
        رحلتك © 2026 — منصة حجز السفر الذكية بالوكلاء
      </footer>
    </div>
  )
}

export default App
