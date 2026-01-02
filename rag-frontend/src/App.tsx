import { useState, useRef, useEffect } from 'react'
import './App.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001'

interface Message {
  role: 'user' | 'assistant'
  content: string
  sources?: string[]
}

interface OllamaModel {
  name: string
  size: number
}

function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [model, setModel] = useState('llama3.2:1b')
  const [availableModels, setAvailableModels] = useState<string[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Fetch available models on component mount
  useEffect(() => {
    const fetchModels = async () => {
      try {
        const response = await fetch(`${API_URL}/models`)
        if (response.ok) {
          const data = await response.json()
          const modelNames = data.models?.map((m: OllamaModel) => m.name) || []
          setAvailableModels(modelNames)
          // Set first available model as default if current model not available
          if (modelNames.length > 0 && !modelNames.includes(model)) {
            setModel(modelNames[0])
          }
        }
      } catch (error) {
        console.error('Failed to fetch models:', error)
        // Fallback to default model
        setAvailableModels(['llama3.2:1b'])
      }
    }
    fetchModels()
  }, [])

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

    // Add empty assistant message that we'll update with streaming tokens
    const assistantMessageIndex = messages.length + 1
    setMessages(prev => [...prev, { role: 'assistant', content: '' }])

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

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      let accumulatedContent = ''
      let sources: string[] = []

      if (reader) {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          const chunk = decoder.decode(value)
          const lines = chunk.split('\n')

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))
                
                if (data.token) {
                  accumulatedContent += data.token
                  // Update the assistant message with accumulated content
                  setMessages(prev => {
                    const newMessages = [...prev]
                    newMessages[assistantMessageIndex] = {
                      role: 'assistant',
                      content: accumulatedContent
                    }
                    return newMessages
                  })
                }
                
                if (data.done) {
                  sources = data.sources || []
                  // Update final message with sources
                  setMessages(prev => {
                    const newMessages = [...prev]
                    newMessages[assistantMessageIndex] = {
                      role: 'assistant',
                      content: accumulatedContent,
                      sources: sources
                    }
                    return newMessages
                  })
                }

                if (data.error) {
                  throw new Error(data.error)
                }
              } catch (e) {
                // Ignore parse errors for incomplete chunks
              }
            }
          }
        }
      }
    } catch (error) {
      console.error('Error:', error)
      setMessages(prev => {
        const newMessages = [...prev]
        newMessages[assistantMessageIndex] = {
          role: 'assistant',
          content: 'Sorry, there was an error processing your request.'
        }
        return newMessages
      })
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
        <h1>📚 Eureka 1854</h1>
        <h2>Historical Document AI Chat</h2>
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
              {availableModels.length > 0 ? (
                availableModels.map(modelName => (
                  <option key={modelName} value={modelName}>{modelName}</option>
                ))
              ) : (
                <option value="llama3.2:1b">Loading models...</option>
              )}
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
