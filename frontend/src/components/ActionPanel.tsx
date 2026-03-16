type ActionPanelProps = {
  title: string
  emoji: string
  children: React.ReactNode
}

export function ActionPanel({ title, emoji, children }: ActionPanelProps) {
  return (
    <div className="action-panel animate-slide-in">
      <div className="action-header">
        <h2 className="action-title">
          <span className="action-emoji">{emoji}</span>
          {title}
        </h2>
      </div>
      <div className="action-content">
        {children}
      </div>
    </div>
  )
}
