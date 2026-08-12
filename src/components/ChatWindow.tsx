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
      <header className="chat-header">
        <h1 className="chat-title">
          <AlertTriangle className="icon-orange" />
          Sentri RCA Console
        </h1>
      </header>

      <main className="chat-main">
        {messages.map((msg) => (
          <div key={msg.id} className={`message-row ${msg.role === 'user' ? 'message-user' : 'message-assistant'}`}>
            <div className={`message-bubble ${msg.role === 'user' ? 'bubble-user' : 'bubble-assistant'}`}>

              {/* If it's an RCA response, render the cards */}
              {msg.rca && (
                <div className="rca-card-container">
                  <div className="rca-card">
                    <h3 className="rca-title title-orange">Root Cause Hypothesis</h3>
                    <p>{msg.rca.hypothesis}</p>
                  </div>
                  <div className="rca-card-row">
                    <div className="rca-card" style={{ flex: 1 }}>
                      <h3 className="rca-title title-green">Confidence Score</h3>
                      <div className="confidence-score">{msg.rca.confidence_score}%</div>
                    </div>
                    <div className="rca-card" style={{ flex: 1 }}>
                      <h3 className="rca-title title-blue">Suggested Fix</h3>
                      <p>{msg.rca.suggested_fix}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Regular markdown/text content */}
              <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>

            </div>
          </div>
        ))}
        {loading && (
          <div className="loading-indicator">
            <Loader2 className="spin" style={{ height: '1rem', width: '1rem' }} />
            Sentri is thinking...
          </div>
        )}
        <div ref={messagesEndRef} />
      </main>

      <footer className="chat-footer">
        <div className="input-container">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="Ask follow-up questions..."
            className="chat-input"
            disabled={loading}
          />
          <button
            onClick={() => sendMessage(input)}
            disabled={loading || !input.trim()}
            className="send-button"
          >
            <Send style={{ height: '1.25rem', width: '1.25rem' }} />
          </button>
        </div>
      </footer>
    </div>
  );
}
