import { useState, useRef, useEffect } from 'react'
import './App.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001'

interface Message {
  role: 'user' | 'assistant'
  content: string
  sources?: string[]
}

function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [model, setModel] = useState('llama3.2:3b')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const sendMessage = async () => {
    if (!input.trim() || loading) return

    const userMessage: Message = { role: 'user', content: input }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: input,
          model: model,
          max_results: 3
        })
      })

      if (!response.ok) {
        throw new Error('Failed to get response')
      }

      const data = await response.json()
      const assistantMessage: Message = {
        role: 'assistant',
        content: data.response,
        sources: data.sources
      }
      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      console.error('Error:', error)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, there was an error processing your request.'
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>📚 Document RAG Chat</h1>
        <p>Ask questions about your historical mining documents</p>
      </header>

      <div className="chat-container">
        <div className="messages">
          {messages.length === 0 && (
            <div className="empty-state">
              <p>👋 Welcome! Ask me anything about the documents.</p>
              <p className="hint">Try: "What gold nuggets were found in Bendigo?"</p>
            </div>
          )}
          
          {messages.map((msg, idx) => (
            <div key={idx} className={`message ${msg.role}`}>
              <div className="message-avatar">
                {msg.role === 'user' ? '👤' : '🤖'}
              </div>
              <div className="message-content">
                <div className="message-text">{msg.content}</div>
                {msg.sources && msg.sources.length > 0 && (
                  <details className="sources">
                    <summary>📄 View Sources</summary>
                    <div className="sources-content">
                      {msg.sources.map((source, i) => (
                        <pre key={i}>{source}</pre>
                      ))}
                    </div>
                  </details>
                )}
              </div>
            </div>
          ))}
          
          {loading && (
            <div className="message assistant">
              <div className="message-avatar">🤖</div>
              <div className="message-content">
                <div className="loading">Thinking...</div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        <div className="input-container">
          <div className="model-selector">
            <label htmlFor="model">Model:</label>
            <select 
              id="model"
              value={model} 
              onChange={(e) => setModel(e.target.value)}
              disabled={loading}
            >
              <option value="llama3.2:3b">Llama 3.2 (3B)</option>
              <option value="llama3.2:1b">Llama 3.2 (1B)</option>
              <option value="qwen2.5:3b">Qwen 2.5 (3B)</option>
              <option value="phi3:mini">Phi-3 Mini</option>
            </select>
          </div>
          
          <div className="input-box">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask a question about your documents..."
              rows={2}
              disabled={loading}
            />
            <button onClick={sendMessage} disabled={loading || !input.trim()}>
              {loading ? '⏳' : '📤'} Send
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
