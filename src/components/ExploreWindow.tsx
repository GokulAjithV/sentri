import React, { useState, useEffect, useRef } from 'react';
import { Send, Search, Loader2 } from 'lucide-react';
import './ChatWindow.css';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

export function ExploreWindow() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [serviceName, setServiceName] = useState('');
  const [availableRepos, setAvailableRepos] = useState<string[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    const fetchRepos = async () => {
      try {
        const apiUrl = import.meta.env.SENTRI_CORE_API_URL || 'http://localhost:8001';
        const res = await fetch(`${apiUrl}/api/config/repos`);
        if (res.ok) {
          const data = await res.json();
          if (data.repos && data.repos.length > 0) {
            setAvailableRepos(data.repos);
            setServiceName(data.repos[0]);
          }
        }
      } catch (err) {
        console.error("Failed to fetch available repos", err);
      }
    };
    fetchRepos();
  }, []);

  const sendMessage = async (messageText: string) => {
    if (!messageText.trim()) return;

    const userMessage: Message = { id: Date.now().toString(), role: 'user', content: messageText };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    const assistantId = (Date.now() + 1).toString();
    setMessages(prev => [...prev, { id: assistantId, role: 'assistant', content: '' }]);

    try {
      const apiUrl = import.meta.env.SENTRI_CORE_API_URL || 'http://localhost:8001';
      const response = await fetch(`${apiUrl}/api/chat/explore`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message: messageText,
          service_name: serviceName,
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

  return (
    <div className="chat-container">
      <div className="chat-header">
        <div className="chat-header-content">
          <div>
            <h1 className="chat-title">Explore Codebase</h1>
            <div className="chat-subtitle">Ask questions about your repositories directly to Sentri.</div>
          </div>
          <div className="service-selector">
            <span className="service-label">Select Repository:</span>
            <select 
              value={serviceName} 
              onChange={(e) => setServiceName(e.target.value)}
              className="service-dropdown"
            >
              {availableRepos.length > 0 ? (
                availableRepos.map(repo => (
                  <option key={repo} value={repo}>{repo}</option>
                ))
              ) : (
                <option value="loading">Loading repos...</option>
              )}
            </select>
          </div>
        </div>
      </div>

      <div className="chat-history">
        {messages.length === 0 ? (
          <div className="empty-state">
            <Search className="empty-icon" size={48} />
            <h2>Codebase Explorer</h2>
            <p>Ask anything about how {serviceName} works.</p>
          </div>
        ) : (
          messages.map(msg => (
            <div key={msg.id} className={`message-wrapper ${msg.role === 'user' ? 'wrapper-user' : 'wrapper-assistant'}`}>
              <div className={`message ${msg.role === 'user' ? 'message-user' : 'message-assistant'}`}>
                {msg.role === 'assistant' && (
                  <div className="message-sender">Sentri</div>
                )}
                <div className="message-content">
                  {msg.content}
                  {msg.role === 'assistant' && !msg.content && loading && (
                    <span className="typing-indicator">...</span>
                  )}
                </div>
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
            placeholder={`Ask a question about ${serviceName}...`}
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
