import { useState, useEffect } from 'react'
import './App.css'

/* ---- Types ---- */

type Destination = { city: string; country: string }
type TravelProgram = {
  city: string
  country: string
  program_name: string
  days: number
  category: string
  approx_budget_per_person: number
  highlights: string
}

type PlannerResponse = {
  itinerary: string
  program_id?: string
  approx_budget_per_person?: number
}

type Hotel = {
  id: string
  name: string
  country: string
  city: string
  stars: number
  price_per_night: number
  currency: string
  near_attraction: string
}

type FlightConfirmation = {
  booking_reference: string
  seat_class: string
  baggage_kg: number
}

const API_BASE = 'http://localhost:8000'

const COUNTRY_FLAGS: Record<string, string> = {
  Spain: '🇪🇸',
  Portugal: '🇵🇹',
  Greece: '🇬🇷',
  Italy: '🇮🇹',
  France: '🇫🇷',
  Germany: '🇩🇪',
  Switzerland: '🇨🇭',
}

const STEP_LABELS = ['الوجهة', 'البرنامج', 'الفنادق', 'الطيران']

/* ---- Component ---- */

function App() {
  const [step, setStep] = useState(0)
  const [animClass, setAnimClass] = useState('card-enter')

  // Step 0: user info + destination
  const [userName, setUserName] = useState('')
  const [userEmail, setUserEmail] = useState('')
  const [destinations, setDestinations] = useState<Destination[]>([])
  const [programs, setPrograms] = useState<TravelProgram[]>([])
  const [selectedCity, setSelectedCity] = useState<string | null>(null)

  // Step 1: itinerary
  const [plannerData, setPlannerData] = useState<PlannerResponse | null>(null)
  const [loading, setLoading] = useState(false)

  // Step 2: hotels
  const [budget, setBudget] = useState<number | ''>('')
  const [minStars, setMinStars] = useState(3)
  const [hotels, setHotels] = useState<Hotel[]>([])
  const [selectedHotelId, setSelectedHotelId] = useState<string | null>(null)

  // Step 3: flight
  const [seatClass, setSeatClass] = useState<'economy' | 'business' | 'first'>('economy')
  const [baggageKg, setBaggageKg] = useState(20)

  // Confirmation modal
  const [confirmation, setConfirmation] = useState<FlightConfirmation | null>(null)
  const [showModal, setShowModal] = useState(false)

  // Load destinations on mount
  useEffect(() => {
    fetch(`${API_BASE}/destinations`)
      .then((r) => r.json())
      .then((data) => {
        setDestinations(data.destinations || [])
        setPrograms(data.programs || [])
      })
      .catch(() => {})
  }, [])

  /* ---- Navigation ---- */

  function goToStep(n: number) {
    setAnimClass('card-exit')
    setTimeout(() => {
      setStep(n)
      setAnimClass('card-enter')
    }, 300)
  }

  /* ---- API calls ---- */

  async function handleGenerateItinerary() {
    if (!selectedCity) return
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/planner/itinerary`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          destination: selectedCity,
          user_name: userName || null,
          user_email: userEmail || null,
        }),
      })
      const data: PlannerResponse = await res.json()
      setPlannerData(data)
      goToStep(1)
    } catch {
      // handle error
    } finally {
      setLoading(false)
    }
  }

  async function handleSearchHotels() {
    if (!selectedCity) return
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/hotels/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          destination: selectedCity,
          budget: budget === '' ? null : Number(budget),
          min_stars: minStars,
        }),
      })
      const data: { hotels: Hotel[] } = await res.json()
      setHotels(data.hotels)
      setSelectedHotelId(data.hotels[0]?.id ?? null)
    } catch {
      // handle error
    } finally {
      setLoading(false)
    }
  }

  async function handleConfirmHotel() {
    if (!selectedCity || !selectedHotelId) return
    await fetch(`${API_BASE}/hotels/select`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        destination: selectedCity,
        selected_hotel_id: selectedHotelId,
      }),
    })
    goToStep(3)
  }

  async function handleConfirmBooking() {
    if (!selectedCity || !selectedHotelId) return
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/flight/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          destination: selectedCity,
          user_name: userName || null,
          user_email: userEmail || null,
          selected_hotel_id: selectedHotelId,
          seat_class: seatClass,
          baggage_kg: baggageKg,
        }),
      })
      const data: FlightConfirmation = await res.json()
      setConfirmation(data)
      setShowModal(true)
    } catch {
      // handle error
    } finally {
      setLoading(false)
    }
  }

  function resetAll() {
    setStep(0)
    setAnimClass('card-enter')
    setSelectedCity(null)
    setPlannerData(null)
    setBudget('')
    setMinStars(3)
    setHotels([])
    setSelectedHotelId(null)
    setSeatClass('economy')
    setBaggageKg(20)
    setConfirmation(null)
    setShowModal(false)
  }

  /* ---- Helpers ---- */

  const selectedDestination = destinations.find((d) => d.city === selectedCity)
  const selectedHotel = hotels.find((h) => h.id === selectedHotelId)
  const cityPrograms = programs.filter((p) => p.city === selectedCity)

  /* ---- Render ---- */

  return (
    <div className="app">
      {/* Header */}
      <header className="app-header">
        <div className="logo">
          رحلت<span>ك</span> ✈️
        </div>
        <div className="header-actions">
          {step > 0 && (
            <button className="btn-secondary" onClick={resetAll}>
              رحلة جديدة
            </button>
          )}
        </div>
      </header>

      {/* Stepper */}
      <nav className="stepper">
        {STEP_LABELS.map((label, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center' }}>
            <div
              className={`step-item ${
                step === i ? 'active' : step > i ? 'completed' : ''
              }`}
            >
              <div className="step-circle">
                {step > i ? '✓' : i + 1}
              </div>
              <span className="step-label">{label}</span>
            </div>
            {i < STEP_LABELS.length - 1 && (
              <div className={`step-line ${step > i ? 'done' : ''}`} />
            )}
          </div>
        ))}
      </nav>

      {/* Main */}
      <main className="app-main">
        {/* Step 0: Destination */}
        {step === 0 && (
          <section className={`card ${animClass}`}>
            <h2>اختر وجهتك ✨</h2>
            <p className="subtitle">أدخل بياناتك الأساسية واختر المدينة اللي عايز تسافرها</p>

            <div className="field-grid">
              <div className="field-row">
                <label>الاسم</label>
                <input
                  id="input-name"
                  value={userName}
                  onChange={(e) => setUserName(e.target.value)}
                  placeholder="اكتب اسمك"
                />
              </div>
              <div className="field-row">
                <label>البريد الإلكتروني</label>
                <input
                  id="input-email"
                  value={userEmail}
                  onChange={(e) => setUserEmail(e.target.value)}
                  placeholder="you@example.com"
                  type="email"
                  dir="ltr"
                />
              </div>
            </div>

            <h2 style={{ marginTop: '8px' }}>الوجهات المتاحة</h2>
            <div className="dest-grid">
              {destinations.map((d) => (
                <div
                  key={d.city}
                  id={`dest-${d.city}`}
                  className={`dest-card ${selectedCity === d.city ? 'selected' : ''}`}
                  onClick={() => setSelectedCity(d.city)}
                >
                  <div className="dest-emoji">
                    {COUNTRY_FLAGS[d.country] || '🌍'}
                  </div>
                  <div className="dest-city">{d.city}</div>
                  <div className="dest-country">{d.country}</div>
                </div>
              ))}
            </div>

            <div className="btn-row">
              <button
                id="btn-plan"
                className="btn-primary"
                disabled={!selectedCity || loading}
                onClick={handleGenerateItinerary}
              >
                {loading ? (
                  <span className="loading-spinner" style={{ padding: 0 }}>
                    <span className="spinner" /> جاري التخطيط...
                  </span>
                ) : (
                  'خطّط رحلتي 🚀'
                )}
              </button>
            </div>
          </section>
        )}

        {/* Step 1: Itinerary */}
        {step === 1 && plannerData && (
          <section className={`card ${animClass}`}>
            <h2>
              برنامج رحلتك إلى {selectedCity}{' '}
              {COUNTRY_FLAGS[selectedDestination?.country || ''] || ''}
            </h2>
            <p className="subtitle">
              {cityPrograms.length > 0
                ? `${cityPrograms[0].program_name} – ${cityPrograms[0].days} أيام`
                : 'برنامج مُقترح'}
            </p>

            <div className="itinerary-box">{plannerData.itinerary}</div>

            {plannerData.approx_budget_per_person && (
              <div className="itinerary-budget">
                💰 الميزانية التقريبية: {plannerData.approx_budget_per_person} USD / شخص
              </div>
            )}

            <div className="btn-row">
              <button className="btn-secondary" onClick={() => goToStep(0)}>
                ← تغيير الوجهة
              </button>
              <button
                id="btn-to-hotels"
                className="btn-primary"
                onClick={() => {
                  goToStep(2)
                  // Auto-search hotels when reaching hotel step
                  setTimeout(() => handleSearchHotels(), 350)
                }}
              >
                اختر فندق 🏨
              </button>
            </div>
          </section>
        )}

        {/* Step 2: Hotels */}
        {step === 2 && (
          <section className={`card ${animClass}`}>
            <h2>اختر فندقك في {selectedCity} 🏨</h2>
            <p className="subtitle">فلتر واختار الفندق المناسب ليك</p>

            <div className="field-grid">
              <div className="field-row">
                <label>الميزانية / الليلة (حد أقصى)</label>
                <input
                  id="input-budget"
                  type="number"
                  min={0}
                  value={budget}
                  onChange={(e) =>
                    setBudget(e.target.value === '' ? '' : Number(e.target.value))
                  }
                  placeholder="بدون حد"
                />
              </div>
              <div className="field-row">
                <label>أقل عدد نجوم</label>
                <select
                  id="select-stars"
                  value={minStars}
                  onChange={(e) => setMinStars(Number(e.target.value))}
                >
                  {[1, 2, 3, 4, 5].map((s) => (
                    <option key={s} value={s}>
                      {s} {'★'.repeat(s)}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <button
              id="btn-search-hotels"
              className="btn-secondary"
              onClick={handleSearchHotels}
              disabled={loading}
              style={{ marginBottom: 8 }}
            >
              {loading ? 'جاري البحث...' : '🔍 بحث'}
            </button>

            {hotels.length > 0 && (
              <div className="hotel-list">
                {hotels.map((h) => (
                  <div
                    key={h.id}
                    id={`hotel-${h.id}`}
                    className={`hotel-card ${
                      selectedHotelId === h.id ? 'hotel-card--selected' : ''
                    }`}
                    onClick={() => setSelectedHotelId(h.id)}
                  >
                    {selectedHotelId === h.id && (
                      <div className="hotel-selected-check">✓</div>
                    )}
                    <div className="hotel-stars">
                      {'★'.repeat(h.stars)}{'☆'.repeat(5 - h.stars)}
                    </div>
                    <div className="hotel-name">{h.name}</div>
                    <div className="hotel-location">
                      📍 {h.city}، {h.country}
                    </div>
                    {h.near_attraction && (
                      <div className="hotel-attraction">
                        🏛️ {h.near_attraction}
                      </div>
                    )}
                    <div className="hotel-price">
                      {h.price_per_night} {h.currency}{' '}
                      <span>/ الليلة</span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {hotels.length === 0 && !loading && (
              <p style={{ color: '#9CA3AF', textAlign: 'center', padding: '20px 0' }}>
                اضغط بحث لعرض الفنادق المتاحة
              </p>
            )}

            <div className="btn-row">
              <button className="btn-secondary" onClick={() => goToStep(1)}>
                ← البرنامج
              </button>
              <button
                id="btn-confirm-hotel"
                className="btn-primary"
                disabled={!selectedHotelId}
                onClick={handleConfirmHotel}
              >
                تأكيد الفندق ✅
              </button>
            </div>
          </section>
        )}

        {/* Step 3: Flight */}
        {step === 3 && (
          <section className={`card ${animClass}`}>
            <h2>حجز الطيران ✈️</h2>
            <p className="subtitle">
              اختر درجة السفر وحدد وزن الحقائب
              {selectedHotel && (
                <span style={{ display: 'block', marginTop: 4, color: '#4F46E5' }}>
                  🏨 {selectedHotel.name} – {selectedHotel.city}
                </span>
              )}
            </p>

            <div className="field-grid">
              <div className="field-row">
                <label>درجة السفر</label>
                <select
                  id="select-seat"
                  value={seatClass}
                  onChange={(e) =>
                    setSeatClass(e.target.value as 'economy' | 'business' | 'first')
                  }
                >
                  <option value="economy">Economy 💺</option>
                  <option value="business">Business 💼</option>
                  <option value="first">First Class 👑</option>
                </select>
              </div>
              <div className="field-row">
                <label>وزن الحقائب (كجم)</label>
                <input
                  id="input-baggage"
                  type="number"
                  min={0}
                  max={40}
                  value={baggageKg}
                  onChange={(e) => setBaggageKg(Number(e.target.value) || 0)}
                />
              </div>
            </div>

            <div className="btn-row">
              <button className="btn-secondary" onClick={() => goToStep(2)}>
                ← الفنادق
              </button>
              <button
                id="btn-confirm-booking"
                className="btn-primary"
                disabled={!selectedHotelId || loading}
                onClick={handleConfirmBooking}
              >
                {loading ? (
                  <span className="loading-spinner" style={{ padding: 0 }}>
                    <span className="spinner" /> جاري الحجز...
                  </span>
                ) : (
                  'تأكيد الحجز النهائي 🎉'
                )}
              </button>
            </div>
          </section>
        )}
      </main>

      {/* Confirmation Modal */}
      {showModal && confirmation && (
        <div className="modal-overlay" onClick={() => { setShowModal(false); resetAll(); }}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => { setShowModal(false); resetAll(); }}>
              ✕
            </button>

            <div className="modal-icon success">🎉</div>
            <h3>تم تأكيد الحجز بنجاح!</h3>
            <p className="modal-subtitle">
              رحلتك إلى {selectedCity} محجوزة وجاهزة
            </p>

            <div className="modal-details">
              <div className="detail-row">
                <span className="detail-label">الوجهة</span>
                <span className="detail-value">
                  {selectedCity} {COUNTRY_FLAGS[selectedDestination?.country || ''] || ''}
                </span>
              </div>
              {selectedHotel && (
                <div className="detail-row">
                  <span className="detail-label">الفندق</span>
                  <span className="detail-value">
                    {selectedHotel.name} {'★'.repeat(selectedHotel.stars)}
                  </span>
                </div>
              )}
              <div className="detail-row">
                <span className="detail-label">درجة السفر</span>
                <span className="detail-value">{confirmation.seat_class}</span>
              </div>
              <div className="detail-row">
                <span className="detail-label">الحقائب</span>
                <span className="detail-value">{confirmation.baggage_kg} كجم</span>
              </div>
              <div className="detail-row">
                <span className="detail-label">رقم الحجز</span>
                <span className="detail-value ref">
                  {confirmation.booking_reference}
                </span>
              </div>
            </div>

            <button className="btn-primary" onClick={() => { setShowModal(false); resetAll(); }} style={{ width: '100%' }}>
              حجز رحلة جديدة 🚀
            </button>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="app-footer">
        رحلتك © 2026 — منصة حجز السفر الذكية بالوكلاء
      </footer>
    </div>
  )
}

export default App
