type Hotel = {
  id: string
  name: string
  stars: number
  price_per_night: number
  currency: string
  city?: string
  sea_view?: boolean
}

type HotelCardProps = {
  hotel: Hotel
  isSelected?: boolean
  onSelect: (hotelId: string) => void
}

export function HotelCard({ hotel, isSelected, onSelect }: HotelCardProps) {
  return (
    <div 
      className={`hotel-card ${isSelected ? 'selected' : ''}`}
      onClick={() => onSelect(hotel.id)}
    >
      <div className="hotel-header">
        <h3 className="hotel-name">{hotel.name}</h3>
        <div className="hotel-stars">
          {'⭐'.repeat(hotel.stars)}
        </div>
      </div>
      
      {hotel.city && (
        <div className="hotel-location">📍 {hotel.city}</div>
      )}
      
      {hotel.sea_view && (
        <div className="hotel-badge">🌊 Sea View</div>
      )}
      
      <div className="hotel-footer">
        <div className="hotel-price">
          <span className="amount">{hotel.price_per_night}</span>
          <span className="currency"> {hotel.currency}/night</span>
        </div>
        <button 
          className={`select-btn ${isSelected ? 'selected' : ''}`}
          onClick={(e) => {
            e.stopPropagation()
            onSelect(hotel.id)
          }}
        >
          {isSelected ? '✓ Selected' : 'Select'}
        </button>
      </div>
    </div>
  )
}
