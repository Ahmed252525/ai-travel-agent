from __future__ import annotations

from typing import Dict, Any

import streamlit as st

from nodes import (
    travel_planner_agent,
    hotel_booking_agent,
    flight_reservation_agent,
)
from state import TravelState


def get_initial_state() -> TravelState:
    """Return an empty initial travel state."""
    return {
        "control": "planner",
        "planner": {},
        "hotel": {},
        "flight": {},
    }


def main() -> None:
    """Simple Streamlit GUI to drive the multi-agent travel flow."""
    st.set_page_config(page_title="Multi-Agent Travel Demo", layout="centered")

    st.title("Multi-Agent Travel Demo (LangGraph-style)")

    # Basic user info (used by final booking confirmation).
    user_name = st.text_input(
        "Your name (optional)",
        value=st.session_state.get("user_name", ""),
    )
    user_email = st.text_input(
        "Your email (optional)",
        value=st.session_state.get("user_email", ""),
    )
    st.session_state["user_name"] = user_name
    st.session_state["user_email"] = user_email

    if "travel_state" not in st.session_state:
        st.session_state.travel_state = get_initial_state()

    travel_state: TravelState = st.session_state.travel_state
    if user_name:
        travel_state["user_name"] = user_name
    if user_email:
        travel_state["user_email"] = user_email

    st.sidebar.header("Internal Control")
    st.sidebar.write(f"Current stage: **{travel_state.get('control', 'planner')}**")

    # --- Step 1: Planner (destination + itinerary) ---
    st.header("1. Travel Planner")
    destination = st.text_input(
        "Destination city",
        value=travel_state.get("planner", {}).get("destination", ""),
        help="مثال: Barcelona, Lisbon, Athens",
    )

    if st.button("Generate Itinerary"):
        if not destination.strip():
            st.warning("من فضلك اكتب وجهة السفر الأول.")
        else:
            travel_state["planner"]["destination"] = destination.strip()
            travel_state["control"] = "planner"
            travel_state = travel_planner_agent(travel_state)
            st.session_state.travel_state = travel_state

    itinerary = travel_state.get("planner", {}).get("itinerary")
    if itinerary:
        st.subheader("Suggested Itinerary")
        st.text(itinerary)

    # --- Step 2: Hotel booking ---
    if travel_state.get("control") in ("hotel", "flight", "done"):
        st.header("2. Hotel Booking")

        col1, col2, col3 = st.columns(3)
        with col1:
            budget = st.number_input(
                "Max budget per night (optional)",
                min_value=0.0,
                value=float(travel_state.get("hotel", {}).get("budget") or 0.0),
            )
            if budget == 0:
                budget_value = None
            else:
                budget_value = budget
        with col2:
            sea_view = st.selectbox(
                "Sea view?",
                options=["No preference", "Yes", "No"],
                index=0,
            )
            if sea_view == "Yes":
                sea_view_value = True
            elif sea_view == "No":
                sea_view_value = False
            else:
                sea_view_value = None
        with col3:
            min_stars = st.slider(
                "Minimum stars",
                min_value=1,
                max_value=5,
                value=int(travel_state.get("hotel", {}).get("min_stars") or 3),
            )

        if st.button("Search Hotels"):
            hotel_state: Dict[str, Any] = travel_state.get("hotel", {})
            hotel_state["budget"] = budget_value
            hotel_state["sea_view"] = sea_view_value
            hotel_state["min_stars"] = int(min_stars)
            hotel_state.pop("selected_hotel_id", None)
            hotel_state.pop("selected_hotel", None)
            travel_state["hotel"] = hotel_state
            travel_state["control"] = "hotel"
            travel_state = hotel_booking_agent(travel_state)
            st.session_state.travel_state = travel_state

        available = travel_state.get("hotel", {}).get("available_hotels", [])

        if available:
            st.subheader("Available Hotels")

            # Map id -> label
            options = {
                h["id"]: f"{h['name']} ({h['city']}) - {h['stars']}★ "
                f"- {h['price_per_night']} {h['currency']} "
                f"{'(Sea view)' if h['sea_view'] else ''}"
                for h in available
            }

            current_selected = travel_state.get("hotel", {}).get(
                "selected_hotel_id",
            )
            default_index = 0
            if current_selected and current_selected in list(options.keys()):
                default_index = list(options.keys()).index(current_selected)

            selected_id = st.selectbox(
                "Choose a hotel",
                options=list(options.keys()),
                format_func=lambda x: options[x],
                index=default_index,
            )

            if st.button("Confirm Hotel"):
                travel_state["hotel"]["selected_hotel_id"] = selected_id
                travel_state["control"] = "hotel"
                travel_state = hotel_booking_agent(travel_state)
                st.session_state.travel_state = travel_state

            selected_hotel = travel_state.get("hotel", {}).get("selected_hotel")
            if selected_hotel:
                st.info(
                    f"Selected hotel: {selected_hotel['name']} in "
                    f"{selected_hotel['city']} ({selected_hotel['stars']}★)",
                )
        else:
            st.write("No hotels loaded yet. اضغط على Search Hotels.")

    # --- Step 3: Flight reservation ---
    if travel_state.get("control") in ("flight", "done"):
        st.header("3. Flight Reservation")

        seat_class = st.selectbox(
            "Seat class",
            options=["economy", "business", "first"],
            index=["economy", "business", "first"].index(
                travel_state.get("flight", {}).get("seat_class", "economy"),
            ),
        )
        baggage_kg = st.slider(
            "Baggage (kg)",
            min_value=0,
            max_value=40,
            value=int(travel_state.get("flight", {}).get("baggage_kg") or 20),
        )

        if st.button("Confirm Booking"):
            travel_state["flight"]["seat_class"] = seat_class
            travel_state["flight"]["baggage_kg"] = int(baggage_kg)
            travel_state["control"] = "flight"
            travel_state = flight_reservation_agent(travel_state)
            st.session_state.travel_state = travel_state

    # --- Final summary ---
    if travel_state.get("control") == "done":
        st.success("Booking completed!")
        st.subheader("Summary")
        st.write("**Destination:**", travel_state["planner"]["destination"])
        st.write("**Itinerary:**")
        st.text(travel_state["planner"]["itinerary"])

        hotel = travel_state["hotel"]["selected_hotel"]
        st.write(
            "**Hotel:**",
            f"{hotel['name']} ({hotel['city']}, {hotel['stars']}★)",
        )
        st.write(
            "**Price per night:**",
            f"{hotel['price_per_night']} {hotel['currency']}",
        )

        flight = travel_state["flight"]
        st.write("**Seat class:**", flight["seat_class"])
        st.write("**Baggage:**", f"{flight['baggage_kg']} kg")
        st.write("**Booking reference:**", flight["booking_reference"])

    if st.button("Reset Flow"):
        st.session_state.travel_state = get_initial_state()
        st.experimental_rerun()


if __name__ == "__main__":
    main()

