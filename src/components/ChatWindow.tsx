import React, { useState, useEffect, useRef } from 'react';
import { Send, AlertTriangle, Loader2 } from 'lucide-react';
import './ChatWindow.css';

interface RCAResult {
  hypothesis: string;
  confidence_score: number;
  suggested_fix: string;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  rca?: RCAResult;
}

export function ChatWindow() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [tokenError, setTokenError] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Use React state for token to ensure hydration is consistent
  const [jwtToken, setJwtToken] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get('token');

    if (!token) {
      setTokenError('Missing Magic Link Token in URL');
      return;
    }

    setJwtToken(token);
  }, []);

  useEffect(() => {
    if (jwtToken && messages.length === 0) {
      // Automatically trigger initial analysis on mount
      sendMessage('INIT');
    }
  }, [jwtToken]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async (messageText: string) => {
    if (!messageText.trim() || !jwtToken) return;

    const userMessage: Message = { id: Date.now().toString(), role: 'user', content: messageText };

    if (messageText !== 'INIT') {
      setMessages(prev => [...prev, userMessage]);
      setInput('');
    }

    setLoading(true);

    // Create a placeholder for the assistant's streaming response
    const assistantId = (Date.now() + 1).toString();
    setMessages(prev => [...prev, { id: assistantId, role: 'assistant', content: '' }]);

    try {
      const apiUrl = import.meta.env.SENTRI_CORE_API_URL || 'http://localhost:8001';
      const response = await fetch(`${apiUrl}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${jwtToken}`
        },
        body: JSON.stringify({
          message: messageText,
          history: messages.map(m => ({ role: m.role, content: m.content }))
        })
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) return;

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6);
            if (dataStr === '[DONE]') continue;

            try {
              const data = JSON.parse(dataStr);

              setMessages(prev => prev.map(msg => {
                if (msg.id === assistantId) {
                  if (data.type === 'token') {
                    return { ...msg, content: msg.content + data.content };
                  } else if (data.type === 'rca') {
                    return { ...msg, rca: data.rca };
                  } else if (data.type === 'error') {
                    return { ...msg, content: msg.content + `\n\n[Error: ${data.message}]` };
                  }
                }
                return msg;
              }));
            } catch (e) {
              console.error('Failed to parse SSE data', dataStr);
            }
          }
        }
      }
    } catch (error: any) {
      setMessages(prev => prev.map(msg =>
        msg.id === assistantId ? { ...msg, content: `Error: ${error.message}` } : msg
      ));
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  if (tokenError) {
    return (
      <div className="error-screen">
        <div className="error-box">
          <AlertTriangle style={{ margin: '0 auto 1rem auto', height: '3rem', width: '3rem', color: '#ef4444' }} />
          <h2 className="error-title">Authentication Error</h2>
          <p style={{ color: '#fca5a5' }}>{tokenError}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-container">
      <div className="chat-header">
        <div className="chat-header-content">
          <div>
            <h1 className="chat-title">Incident RCA</h1>
            <div className="chat-subtitle">Automated root cause analysis and incident context.</div>
          </div>
        </div>
      </div>

      <div className="chat-history">
        {messages.length === 0 ? (
          <div className="empty-state">
            <AlertTriangle className="empty-icon" size={48} />
            <h2>RCA Console</h2>
            <p>Initializing analysis for this incident...</p>
          </div>
        ) : (
          messages.map(msg => (
            <div key={msg.id} className={`message-wrapper ${msg.role === 'user' ? 'wrapper-user' : 'wrapper-assistant'}`}>
              <div className={`message ${msg.role === 'user' ? 'message-user' : 'message-assistant'}`}>
                {msg.role === 'assistant' && (
                  <div className="message-sender">Sentri</div>
                )}
                
                {/* Regular text content */}
                <div className="message-content">
                  {msg.content}
                  {msg.role === 'assistant' && !msg.content && loading && !msg.rca && (
                    <span className="typing-indicator">...</span>
                  )}
                </div>
                
                {/* RCA Card Rendering */}
                {msg.rca && (
                  <div className="rca-card">
                    <div className="rca-header">
                      <AlertTriangle size={18} />
                      Automated RCA Report
                    </div>
                    <div className="rca-body">
                      <div className="rca-section">
                        <h4>Root Cause Hypothesis</h4>
                        <p>{msg.rca.hypothesis}</p>
                      </div>
                      <div className="rca-section">
                        <h4>Confidence Score</h4>
                        <div className="confidence-score">{msg.rca.confidence_score}%</div>
                      </div>
                      <div className="rca-section">
                        <h4>Suggested Fix</h4>
                        <p>{msg.rca.suggested_fix}</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-container">
        <div className="chat-input-wrapper">
          <textarea
            className="chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="Ask follow-up questions..."
            disabled={loading}
            rows={1}
          />
          <button 
            className="send-button"
            onClick={() => sendMessage(input)}
            disabled={!input.trim() || loading}
          >
            {loading ? <Loader2 className="spinner" size={20} /> : <Send size={20} />}
          </button>
        </div>
      </div>
    </div>
  );
}
