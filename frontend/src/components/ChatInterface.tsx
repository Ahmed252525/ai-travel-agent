import { useState, useRef, useEffect } from 'react';
import { useChatWebSocket } from '../hooks/useChatWebSocket';
import { ChatMessage } from './ChatMessage';

export function ChatInterface() {
  const { messages, sendMessage, sendAction, isConnecting } = useChatWebSocket('ws://localhost:8000/chat');
  const [input, setInput] = useState('');
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isConnecting) return;
    sendMessage(input);
    setInput('');
  };

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <h3>المساعد الذكي 🤖</h3>
      </div>
      <div className="chat-messages">
        {messages.map((m) => (
          <ChatMessage 
            key={m.id} 
            role={m.role} 
            content={m.content} 
            options={m.options}
            onAction={sendAction}
            isLoading={m.isStreaming}
          />
        ))}
        {isConnecting && <div className="chat-status">Connecting to agent...</div>}
        <div ref={endRef} />
      </div>
      <form className="chat-input-form" onSubmit={handleSubmit}>
        <input 
          value={input} 
          onChange={e => setInput(e.target.value)} 
          placeholder="ابحث عن رحلتك هنا..."
          className="chat-input"
          disabled={isConnecting}
        />
        <button type="submit" className="chat-submit-btn" disabled={!input.trim() || isConnecting}>
          إرسال
        </button>
      </form>
    </div>
  );
}
