type FlightOptionProps = {
  label: string
  description: string
  emoji: string
  baggage: string
  isSelected?: boolean
  onSelect: () => void
}

export function FlightOption({
  label,
  description,
  emoji,
  baggage,
  isSelected,
  onSelect
}: FlightOptionProps) {
  return (
    <button
      className={`flight-option ${isSelected ? 'selected' : ''}`}
      onClick={onSelect}
    >
      <div className="flight-emoji">{emoji}</div>
      <div className="flight-content">
        <h4 className="flight-label">{label}</h4>
        <p className="flight-description">{description}</p>
        <div className="flight-baggage">🧳 {baggage}</div>
      </div>
      {isSelected && <div className="flight-checkmark">✓</div>}
    </button>
  )
}
