from __future__ import annotations

from typing import Any, Dict, List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from nodes import (
    flight_reservation_agent,
    hotel_booking_agent,
    travel_planner_agent,
)
from state import TravelState
from supabase_client import get_supabase


app = FastAPI(title="Multi-Agent Travel API")

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


