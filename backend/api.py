from __future__ import annotations

from typing import Any, Dict, List

import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from nodes import (
    flight_reservation_agent,
    hotel_booking_agent,
    travel_planner_agent,
)
from state import TravelState
from supabase_client import get_supabase
from graph import build_travel_graph

app = FastAPI(title="Multi-Agent Travel API")
graph = build_travel_graph()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/destinations")
def list_destinations() -> Dict[str, Any]:
    """Return unique destinations from travel_programs table."""
    supabase = get_supabase()
    res = (
        supabase.table("travel_programs")
        .select("city,country,program_name,days,category,approx_budget_per_person,highlights")
        .execute()
    )
    programs: List[Dict[str, Any]] = res.data or []
    # Build a unique city list with their country
    seen: dict[str, Dict[str, Any]] = {}
    for p in programs:
        city = p.get("city", "")
        if city not in seen:
            seen[city] = {"city": city, "country": p.get("country", "")}
    return {"destinations": list(seen.values()), "programs": programs}


@app.post("/planner/itinerary")
def planner_itinerary(payload: Dict[str, Any]) -> Dict[str, Any]:
    destination: str = payload.get("destination", "")
    user_name: str | None = payload.get("user_name")
    user_email: str | None = payload.get("user_email")

    state: TravelState = {
        "control": "planner",
        "planner": {"destination": destination},
        "hotel": {},
        "flight": {},
    }
    if user_name:
        state["user_name"] = user_name
    if user_email:
        state["user_email"] = user_email

    new_state = travel_planner_agent(state)
    planner_state = new_state["planner"]
    return {
        "itinerary": planner_state.get("itinerary", ""),
        "program_id": planner_state.get("program_id"),
        "approx_budget_per_person": planner_state.get("approx_budget_per_person"),
    }


@app.post("/hotels/search")
def hotels_search(payload: Dict[str, Any]) -> Dict[str, Any]:
    destination: str = payload.get("destination", "")
    budget = payload.get("budget")
    min_stars = payload.get("min_stars")

    state: TravelState = {
        "control": "hotel",
        "planner": {"destination": destination},
        "hotel": {
            "budget": budget,
            "min_stars": min_stars,
        },
        "flight": {},
    }

    new_state = hotel_booking_agent(state)
    hotels = new_state["hotel"].get("available_hotels", [])
    return {"hotels": hotels}


@app.post("/hotels/select")
def hotels_select(payload: Dict[str, Any]) -> Dict[str, Any]:
    destination: str = payload.get("destination", "")
    selected_hotel_id: str = payload.get("selected_hotel_id", "")

    state: TravelState = {
        "control": "hotel",
        "planner": {"destination": destination},
        "hotel": {"selected_hotel_id": selected_hotel_id},
        "flight": {},
    }
    new_state = hotel_booking_agent(state)
    return {"selected_hotel": new_state["hotel"].get("selected_hotel")}


@app.post("/flight/confirm")
def flight_confirm(payload: Dict[str, Any]) -> Dict[str, Any]:
    destination: str = payload.get("destination", "")
    user_name: str | None = payload.get("user_name")
    user_email: str | None = payload.get("user_email")
    selected_hotel_id: str = payload.get("selected_hotel_id", "")
    seat_class: str = payload.get("seat_class", "economy")
    baggage_kg: int = int(payload.get("baggage_kg", 20))

    # First make sure we have the selected hotel in state via hotel agent.
    hotel_state: TravelState = {
        "control": "hotel",
        "planner": {"destination": destination},
        "hotel": {"selected_hotel_id": selected_hotel_id},
        "flight": {},
    }
    hotel_state = hotel_booking_agent(hotel_state)

    state: TravelState = {
        "control": "flight",
        "planner": {"destination": destination},
        "hotel": hotel_state["hotel"],
        "flight": {
            "seat_class": seat_class,
            "baggage_kg": baggage_kg,
        },
    }
    if user_name:
        state["user_name"] = user_name
    if user_email:
        state["user_email"] = user_email

    new_state = flight_reservation_agent(state)
    flight_state = new_state["flight"]
    return {
        "booking_reference": flight_state.get("booking_reference"),
        "seat_class": flight_state.get("seat_class"),
        "baggage_kg": flight_state.get("baggage_kg"),
    }


@app.websocket("/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()

    state: TravelState = {
        "control": "conversation",
        "messages": [],
        "summary": "",
        "planner": {},
        "hotel": {},
        "flight": {}
    }

    config = {"configurable": {"websocket": websocket}}

    try:
        while True:
            data_str = await websocket.receive_text()
            try:
                data = json.loads(data_str)
            except json.JSONDecodeError:
                continue

            msg_type = data.get("type")
            if msg_type == "user_message":
                state["messages"].append({"role": "user", "content": data.get("content", "")})
            elif msg_type == "action":
                action = data.get("action")
                payload = data.get("payload", {})
                
                # Append user's action to history so LLM knows what they did
                action_text = f"User selected action: {action}"
                if payload:
                    action_text += f" with payload {payload}"
                state["messages"].append({"role": "user", "content": action_text})

                if action == "trigger_planner":
                    state["control"] = "planner"
                elif action == "set_destination":
                    state["planner"]["destination"] = payload.get("destination")
                    state["control"] = "planner"
                elif action == "select_program":
                    state["control"] = "planner"
                    state["planner"]["selected_program_id"] = payload.get("program_id")
                elif action == "trigger_hotel":
                    state["control"] = "hotel"
                elif action == "select_hotel":
                    state["control"] = "hotel"
                    state["hotel"]["selected_hotel_id"] = payload.get("hotel_id")
                elif action == "trigger_flight":
                    state["control"] = "flight"
                    if "seat_class" in payload:
                        state["flight"]["seat_class"] = payload["seat_class"]
                    if "baggage_kg" in payload:
                        state["flight"]["baggage_kg"] = payload["baggage_kg"]
                elif action == "select_flight":
                    state["control"] = "flight"
                    state["flight"]["selected_flight_id"] = payload.get("flight_id")
                elif action == "confirm_booking":
                    state["control"] = "flight"
                    state["flight"]["user_confirmed"] = True

            # Always route starting with whatever control is set to
            state = await graph.ainvoke(state, config=config)
            
            # If the booking was just confirmed, send confirmation to frontend
            if state.get("control") == "done":
                confirmation = state.get("flight", {}).get("booking_confirmation", "")
                if confirmation:
                    await websocket.send_json({"type": "token", "content": "\n\n" + confirmation})
                await websocket.send_json({"type": "end_of_message"})
                booking_ref_val = state.get("flight", {}).get("booking_reference", "UNKNOWN")
                await websocket.send_json({"type": "booking_done", "booking_reference": booking_ref_val})
                
                # Append a system note so the LLM remembers the booking happened
                msgs = state.get("messages", [])
                msgs.append({"role": "system", "content": f"SYSTEM NOTE: The booking was just successfully confirmed and saved to the database. Reference: {booking_ref_val}. The user may ask questions about it or start a new booking."})

                # Reset state so user can start a new booking if they want
                state = {
                    "control": "conversation",
                    "messages": msgs,
                    "summary": "",
                    "planner": {},
                    "hotel": {},
                    "flight": {}
                }

    except WebSocketDisconnect:
        print("Client disconnected")
