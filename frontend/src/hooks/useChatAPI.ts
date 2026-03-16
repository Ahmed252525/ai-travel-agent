import { useCallback } from 'react'

const API_BASE = '/api'

export function useChatAPI() {
  const sendMessage = useCallback(async (sessionId: string, message: string) => {
    const response = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, message })
    })

    if (!response.body) throw new Error('No response body')
    return response.body.getReader()
  }, [])

  const resumeAction = useCallback(async (sessionId: string, actionData: any) => {
    const response = await fetch(`${API_BASE}/resume`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        session_id: sessionId,
        message: actionData.message || '',
        data: {
          destination: actionData.destination,
          hotel_id: actionData.hotel_id,
          hotel_name: actionData.hotel_name,
          hotel_price: actionData.hotel_price,
          seat_class: actionData.seat_class,
          baggage_kg: actionData.baggage_kg
        }
      })
    })
    return response.json()
  }, [])

  return { sendMessage, resumeAction }
}
