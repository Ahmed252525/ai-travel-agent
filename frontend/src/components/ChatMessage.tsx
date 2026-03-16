import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ActionButton } from './ActionButton'

type ActionOption = {
  label: string;
  action: string;
  payload: any;
};

type MessageProps = {
  role: 'user' | 'assistant'
  content: string
  isLoading?: boolean
  options?: ActionOption[]
  onAction?: (action: string, payload: any, label: string) => void
}

export function ChatMessage({ role, content, isLoading, options, onAction }: MessageProps) {
  return (
    <div className={`message-wrapper message-${role}`}>
      <div className="message-avatar">
        {role === 'user' ? '👤' : '🤖'}
      </div>
      <div className="message-content">
        {isLoading ? (
          <div className="loading-dots">
            <span className="dot"></span>
            <span className="dot"></span>
            <span className="dot"></span>
          </div>
        ) : (
          <div className="message-bubble">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {content}
            </ReactMarkdown>
            {options && options.length > 0 && onAction && (
              <div className="message-options">
                {options.map((opt, i) => (
                  <ActionButton 
                    key={i} 
                    label={opt.label} 
                    onClick={() => onAction(opt.action, opt.payload, opt.label)} 
                  />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
