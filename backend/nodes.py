from __future__ import annotations

from typing import List

from supabase_client import (
    get_flights_for_destination,
    get_hotels_for_city,
    get_travel_program_for_city,
    insert_booking,
)
from state import TravelState, HotelRecord


CITY_TO_AIRPORT = {
    "Barcelona": "BCN",
    "Lisbon": "LIS",
    "Porto": "OPO",
    "Athens": "ATH",
    "Santorini": "SAN",
    "Rome": "ROM",
    "Paris": "CDG",
    "Berlin": "BER",
    "Zurich": "ZRH",
}


def get_hotels() -> List[HotelRecord]:
    """
    Fetch hotels for all cities from Supabase and cast them to HotelRecord.
    """
    # We fetch per-city in the agent, so this helper is unused now.
    raise NotImplementedError("Use get_hotels_for_city via Supabase instead.")


def travel_planner_agent(state: TravelState) -> TravelState:
    """
    Travel Planner Agent.

    - Expects ``state["planner"]["destination"]`` to be set from user input.
    - Creates a simple itinerary and hands off to the hotel agent by
      setting ``state["control"] = "hotel"``.

    Internal reasoning (e.g. LLM chains) stays in local variables only.
    """
    planner_state = state.get("planner", {})

    destination = planner_state.get("destination")
    if not destination:
        raise ValueError(
            "Planner state requires 'destination' to be set before planning.",
        )

    # First agent: read from Supabase travel_programs table.
    program = get_travel_program_for_city(destination)
    if program:
        name = program.get("program_name", "Travel Program")
        days = program.get("days", 3)
        highlights = program.get("highlights", "")
        itinerary = f"{name} ({days} days) in {destination}:\n{highlights}"
        planner_state["program_id"] = program.get("id")
        planner_state["approx_budget_per_person"] = program.get(
            "approx_budget_per_person",
        )
    else:
        itinerary = (
            f"3-day itinerary for {destination}:\n"
            f"- Day 1: Arrival and city exploration in {destination}.\n"
            f"- Day 2: Guided tour and local cuisine.\n"
            f"- Day 3: Free time and departure."
        )

    planner_state["itinerary"] = itinerary
    state["planner"] = planner_state

    # Hand off control to the hotel agent.
    state["control"] = "hotel"
    return state


def hotel_booking_agent(state: TravelState) -> TravelState:
    """
    Hotel Booking Agent.

    Inputs (from user and planner):
      - ``state["planner"]["destination"]``
      - ``state["hotel"]["budget"]`` (optional)
      - ``state["hotel"]["sea_view"]`` (optional)
      - ``state["hotel"]["min_stars"]`` (optional)
      - ``state["hotel"]["selected_hotel_id"]`` (optional, set after pick)

    Behavior:
      - If ``selected_hotel_id`` is not set:
          * Filter hotels to produce ``available_hotels``.
          * Keep ``control = "hotel"`` so the caller can present options
            and update ``selected_hotel_id``.
      - If ``selected_hotel_id`` is set:
          * Lock in ``selected_hotel``.
          * Hand off control to flight agent.
    """
    planner_state = state.get("planner", {})
    hotel_state = state.get("hotel", {})

    destination = planner_state.get("destination")
    if not destination:
        raise ValueError(
            "Hotel agent requires 'planner.destination' to determine city.",
        )

    budget = hotel_state.get("budget")
    min_stars = hotel_state.get("min_stars") or 1
    selected_hotel_id = hotel_state.get("selected_hotel_id")

    # Second agent: fetch hotels for this city from Supabase.
    hotels_db = get_hotels_for_city(destination)

    # If user has already selected a hotel, finalize and hand off.
    if selected_hotel_id:
        matching = [h for h in hotels_db if h["id"] == selected_hotel_id]
        if not matching:
            raise ValueError(f"No hotel found with id '{selected_hotel_id}'.")
        hotel_state["selected_hotel"] = matching[0]
        state["hotel"] = hotel_state
        state["control"] = "flight"
        return state

    # Otherwise prepare options for the user to choose from.
    filtered: List[HotelRecord] = []
    for hotel in hotels_db:
        if hotel["stars"] < min_stars:
            continue
        if budget is not None and hotel["price_per_night"] > budget:
            continue
        filtered.append(hotel)

    hotel_state["available_hotels"] = filtered
    state["hotel"] = hotel_state

    # Stay in the hotel stage until the caller sets ``selected_hotel_id``.
    state["control"] = "hotel"
    return state


def flight_reservation_agent(state: TravelState) -> TravelState:
    """
    Flight Reservation Agent.

    Inputs:
      - ``state["planner"]["destination"]``
      - ``state["hotel"]["selected_hotel"]``
      - ``state["flight"]["seat_class"]``  (economy/business/first)
      - ``state["flight"]["baggage_kg"]``

    Output:
      - ``state["flight"]["booking_reference"]``
      - ``state["control"] = "done"``
    """
    planner_state = state.get("planner", {})
    hotel_state = state.get("hotel", {})
    flight_state = state.get("flight", {})

    destination = planner_state.get("destination")
    selected_hotel = hotel_state.get("selected_hotel")
    seat_class = flight_state.get("seat_class")
    baggage_kg = flight_state.get("baggage_kg")

    if not destination:
        raise ValueError("Flight agent requires 'planner.destination'.")
    if not selected_hotel:
        raise ValueError("Flight agent requires a 'selected_hotel'.")
    if not seat_class:
        raise ValueError("Flight agent requires 'flight.seat_class'.")
    if baggage_kg is None:
        raise ValueError("Flight agent requires 'flight.baggage_kg'.")

    # Third agent: choose a flight from Supabase based on destination + seat_class.
    airport_code = CITY_TO_AIRPORT.get(destination, destination[:3].upper())
    flights = get_flights_for_destination(airport_code, seat_class)
    chosen_flight = flights[0] if flights else None

    reference = (
        f"TRIP-{airport_code}-{selected_hotel['id']}-"
        f"{seat_class[:1].upper()}{baggage_kg}"
    )

    flight_state["booking_reference"] = reference
    if chosen_flight:
        flight_state["flight_id"] = chosen_flight.get("id")
        flight_state["base_price"] = chosen_flight.get("base_price")
        flight_state["currency"] = chosen_flight.get("currency")
    state["flight"] = flight_state

    # Persist confirmation in Supabase bookings table.
    insert_booking(
        {
            # simple demo placeholders for user info
            "user_name": state.get("user_name", "demo_user"),
            "user_email": state.get("user_email", "demo@example.com"),
            "destination": destination,
            "program_id": state.get("planner", {}).get("program_id"),
            "hotel_id": selected_hotel["id"],
            "flight_id": flight_state.get("flight_id"),
            "seat_class": seat_class,
            "baggage_kg": int(baggage_kg),
            "total_price": flight_state.get("base_price"),
            "currency": flight_state.get("currency"),
            "booking_reference": reference,
        },
    )

    # End of flow.
    state["control"] = "done"
    return state

