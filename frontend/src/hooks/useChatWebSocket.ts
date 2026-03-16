import { useState, useEffect, useCallback, useRef } from 'react';

export type ActionOption = {
  label: string;
  action: string;
  payload: any;
};

export type Message = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  options?: ActionOption[];
  isStreaming?: boolean;
};

export function useChatWebSocket(url: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const ws = useRef<WebSocket | null>(null);
  const [isConnecting, setIsConnecting] = useState(false);
  
  // To handle streaming message
  const [currentStream, setCurrentStream] = useState<Message | null>(null);

  useEffect(() => {
    setIsConnecting(true);
    ws.current = new WebSocket(url);
    
    ws.current.onopen = () => {
      setIsConnecting(false);
    };
    
    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'token') {
        setCurrentStream(prev => {
          if (!prev) {
            return { id: Date.now().toString() + Math.random().toString(), role: 'assistant', content: data.content, isStreaming: true };
          }
          return { ...prev, content: prev.content + data.content };
        });
      } else if (data.type === 'action_options') {
        setCurrentStream(prev => {
          if (!prev) return prev;
          return { ...prev, options: data.options };
        });
      } else if (data.type === 'end_of_message') {
        setCurrentStream(prev => {
          if (prev) {
            setMessages(m => {
              if (m.some(msg => msg.id === prev.id)) return m;
              return [...m, { ...prev, isStreaming: false }];
            });
          }
          return null;
        });
      }
    };
    
    ws.current.onclose = () => {
      setIsConnecting(false);
    };
    
    return () => {
      ws.current?.close();
    };
  }, [url]);

  const sendMessage = useCallback((content: string) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      const msg: Message = { id: Date.now().toString() + Math.random().toString(), role: 'user', content };
      setMessages(prev => [...prev, msg]);
      ws.current.send(JSON.stringify({ type: 'user_message', content }));
    }
  }, []);

  const sendAction = useCallback((action: string, payload: any, label?: string) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      if (label) {
        setMessages(prev => [...prev, { id: Date.now().toString() + Math.random().toString(), role: 'user', content: `Selected: ${label}` }]);
      }
      ws.current.send(JSON.stringify({ type: 'action', action, payload }));
    }
  }, []);

  // Combine messages + currentStream
  const displayMessages = currentStream ? [...messages, currentStream] : messages;

  return { messages: displayMessages, sendMessage, sendAction, isConnecting };
}
