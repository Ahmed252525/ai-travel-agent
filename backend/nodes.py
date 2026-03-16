from __future__ import annotations

from typing import List
import json
from langchain_core.runnables import RunnableConfig

from supabase_client import (
    get_flights_for_destination,
    get_hotels_for_city,
    get_travel_programs_for_city,
    insert_booking,
)
from state import TravelState, HotelRecord
from groq_client import call_groq_streaming, call_groq

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
    - Fetches all travel programs for the destination.
    - If a program is selected, locks it in and hands off to the hotel agent.
    """
    planner_state = state.get("planner", {})

    destination = planner_state.get("destination")
    if not destination:
        raise ValueError(
            "Planner state requires 'destination' to be set before planning.",
        )

    # If user has already selected a program, finalize and hand off.
    selected_program_id = planner_state.get("selected_program_id")
    programs = get_travel_programs_for_city(destination)

    if selected_program_id:
        matching = [p for p in programs if p["id"] == selected_program_id]
        if not matching:
            raise ValueError(f"No program found with id '{selected_program_id}'.")
        selected = matching[0]
        planner_state["selected_program"] = selected
        planner_state["approx_budget_per_person"] = selected.get("approx_budget_per_person")
        planner_state["itinerary"] = f"{selected.get('program_name')} ({selected.get('days')} days) in {destination}:\n{selected.get('highlights', '')}"
        state["planner"] = planner_state
        state["control"] = "conversation"
        return state

    # Otherwise prepare options for the user to choose from.
    planner_state["available_programs"] = programs
    if not programs:
        planner_state["itinerary"] = (
            f"3-day itinerary for {destination}:\n"
            f"- Day 1: Arrival and city exploration in {destination}.\n"
            f"- Day 2: Guided tour and local cuisine.\n"
            f"- Day 3: Free time and departure."
        )

    state["planner"] = planner_state
    state["control"] = "conversation"
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
          * Keeps ``control = "conversation"``.
      - If ``selected_hotel_id`` is set:
          * Lock in ``selected_hotel``.
          * Returns control to "conversation".
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
    hotel_state["searched"] = True

    # If user has already selected a hotel, finalize and hand off.
    if selected_hotel_id:
        if selected_hotel_id == "none":
            hotel_state["selected_hotel"] = {
                "id": "none",
                "name": "No Hotel Available",
                "stars": 0,
                "price_per_night": 0,
                "currency": "USD",
                "near_attraction": "N/A"
            }
        else:
            matching = [h for h in hotels_db if h["id"] == selected_hotel_id]
            if not matching:
                raise ValueError(f"No hotel found with id '{selected_hotel_id}'.")
            hotel_state["selected_hotel"] = matching[0]
        state["hotel"] = hotel_state
        state["control"] = "conversation"
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

    # Stay in the conversation stage until the caller sets ``selected_hotel_id``.
    state["control"] = "conversation"
    return state

async def flight_reservation_agent(state: TravelState, config: RunnableConfig) -> TravelState:
    """
    Flight Reservation Agent.

    Inputs:
      - ``state["planner"]["destination"]``
      - ``state["hotel"]["selected_hotel"]``
      - ``state["flight"]["seat_class"]``  (economy/business/first)
      - ``state["flight"]["baggage_kg"]``
      - ``state["flight"]["selected_flight_id"]`` (optional)
      - ``state["flight"]["user_confirmed"]`` (optional)

    Output:
      - ``state["flight"]["booking_reference"]``
      - ``state["flight"]["booking_confirmation"]``
      - ``state["control"] = "done"``
    """
    planner_state = state.get("planner", {})
    hotel_state = state.get("hotel", {})
    flight_state = state.get("flight", {})

    destination = planner_state.get("destination")
    selected_hotel = hotel_state.get("selected_hotel")
    seat_class = flight_state.get("seat_class")
    baggage_kg = flight_state.get("baggage_kg", 20)
    selected_flight_id = flight_state.get("selected_flight_id")
    user_confirmed = flight_state.get("user_confirmed")

    if not destination:
        raise ValueError("Flight agent requires 'planner.destination'.")
    if not selected_hotel:
        raise ValueError("Flight agent requires a 'selected_hotel'.")
    if not seat_class:
        raise ValueError("Flight agent requires 'flight.seat_class'.")

    # Third agent: fetch flights from Supabase based on destination + seat_class.
    airport_code = CITY_TO_AIRPORT.get(destination, destination[:3].upper())
    flights = get_flights_for_destination(airport_code, seat_class)
    flight_state["searched"] = True
    
    if selected_flight_id:
        if selected_flight_id == "none":
            flight_state["selected_flight"] = {
                "id": "none",
                "airline": "No Flights Available",
                "origin": "N/A",
                "base_price": 0,
                "currency": "USD",
                "baggage_included_kg": 0,
                "extra_baggage_price_per_kg": 0
            }
        else:
            matching = [f for f in flights if f["id"] == selected_flight_id]
            if not matching:
                raise ValueError(f"No flight found with id '{selected_flight_id}'.")
            flight_state["selected_flight"] = matching[0]
        
        # Check if user has explicitly confirmed
        if user_confirmed:
            chosen_flight = matching[0]
            reference = (
                f"TRIP-{airport_code}-{selected_hotel['id']}-"
                f"{seat_class[:1].upper()}{baggage_kg}"
            )
            flight_state["booking_reference"] = reference
            
            # Generate bilingual confirmation via LLM
            # Detect language from recent user messages
            history_str = " | ".join([
                m["content"] for m in state.get("messages", [])[-10:]
                if m["role"] == "user" and not m["content"].startswith("User selected")
            ])
            lang_hint = "Arabic" if any(ord(c) > 0x600 for c in history_str) else "English"

            selected_prog = planner_state.get("selected_program", {})
            conf_system = (
                f"You are a travel booking confirmation system. Respond ONLY in {lang_hint}. "
                "Output ONLY the confirmation message — no explanation, no reasoning, no translation notes."
            )
            conf_user = (
                f"Write a short, warm booking confirmation message for the following booking:\n"
                f"- Booking Reference: {reference}\n"
                f"- Destination: {destination}\n"
                f"- Travel Program: {selected_prog.get('program_name', 'N/A')} ({selected_prog.get('days', '')} days, {selected_prog.get('category', '')})\n"
                f"- Hotel: {selected_hotel['name']} ({selected_hotel.get('stars', '')}★, near {selected_hotel.get('near_attraction', '')})\n"
                f"- Flight: {chosen_flight.get('airline')} — {chosen_flight.get('origin')} to {airport_code} ({seat_class} class, {chosen_flight.get('baggage_included_kg', baggage_kg)}kg baggage included)\n"
                f"- Price: {chosen_flight.get('base_price')} {chosen_flight.get('currency')}\n"
                f"Output ONLY the confirmation message in {lang_hint}. Do not add any explanation."
            )
            try:
                confirmation_res = await call_groq(
                    [{"role": "system", "content": conf_system}, {"role": "user", "content": conf_user}],
                    model="llama-3.3-70b-versatile"
                )
            except Exception:
                if lang_hint == "Arabic":
                    confirmation_res = f"تم تأكيد حجزك بنجاح! رقم الحجز: {reference}. وجهتك: {destination}، فندق: {selected_hotel['name']}."
                else:
                    confirmation_res = f"Booking confirmed! Reference: {reference}. Destination: {destination}, Hotel: {selected_hotel['name']}."
            
            flight_state["booking_confirmation"] = confirmation_res
            
            # Persist confirmation in Supabase bookings table.
            insert_booking(
                {
                    "user_name": state.get("user_name", "demo_user"),
                    "user_email": state.get("user_email", "demo@example.com"),
                    "destination": destination,
                    "program_id": planner_state.get("selected_program", {}).get("id"),
                    "hotel_id": selected_hotel["id"],
                    "flight_id": chosen_flight["id"],
                    "seat_class": seat_class,
                    "baggage_kg": int(baggage_kg),
                    "total_price": chosen_flight.get("base_price"),
                    "currency": chosen_flight.get("currency"),
                    "booking_reference": reference,
                },
            )
            state["flight"] = flight_state
            # End of flow.
            state["control"] = "done"
            return state
            
        else:
            # We have a flight but no confirm yet. 
            state["flight"] = flight_state
            state["control"] = "conversation"
            return state

    # Otherwise set available flights and return to conversation
    flight_state["available_flights"] = flights
    state["flight"] = flight_state
    state["control"] = "conversation"
    return state


async def conversation_agent(state: TravelState, config: RunnableConfig) -> TravelState:
    """
    Conversation Agent.
    
    - Reads the full chat history (`messages`).
    - Streams tokens back to the client via `websocket`.
    - Handles handoffs by setting `control` and sub-states.
    """
    websocket = config.get("configurable", {}).get("websocket")
    messages = state.get("messages", [])
    
    planner_state = dict(state.get("planner", {}))
    hotel_state = dict(state.get("hotel", {}))
    flight_state = state.get("flight", {})

    # Arabic → English city name mapping (to match Supabase records)
    ARABIC_TO_ENGLISH_CITY = {
        "برشلونة": "Barcelona",
        "لشبونة": "Lisbon",
        "بورتو": "Porto",
        "أثينا": "Athens",
        "سانتوريني": "Santorini",
        "روما": "Rome",
        "باريس": "Paris",
        "برلين": "Berlin",
        "زيورخ": "Zurich",
    }

    pending_control = "conversation"

    # Try to extract parameters if the user just spoke naturally
    user_msg_content = messages[-1]["content"] if messages and messages[-1]["role"] == "user" else ""
    if user_msg_content and not user_msg_content.startswith("User selected action:"):
        # Provide current context options so the extractor can map phrases like "the first one" or a name to an ID
        avail_ctx = ""
        if planner_state.get("available_programs") and not planner_state.get("selected_program"):
            avail_ctx += "Available Programs:\n" + "\n".join([f"- ID: {p['id']}, Name: {p['program_name']}" for p in planner_state["available_programs"]]) + "\n"
        if hotel_state.get("available_hotels") and not hotel_state.get("selected_hotel"):
            avail_ctx += "Available Hotels:\n" + "\n".join([f"- ID: {h['id']}, Name: {h['name']}" for h in hotel_state["available_hotels"]]) + "\n"
        if flight_state.get("available_flights") and not flight_state.get("selected_flight"):
            avail_ctx += "Available Flights:\n" + "\n".join([f"- ID: {f['id']}, Airline: {f['airline']}" for f in flight_state["available_flights"]]) + "\n"

        extract_prompt = (
            "Extract the following from the user's message if mentioned. "
            "Return ONLY a JSON object with strictly these keys: "
            "'destination' (string, city name in English), "
            "'budget' (number), "
            "'seat_class' (string, 'economy' or 'business'), "
            "'selected_program_id' (string, the ID if user picked one of the Available Programs below, e.g. 'first one' means the first ID), "
            "'selected_hotel_id' (string, the ID if user picked one of the Available Hotels below), "
            "'selected_flight_id' (string, the ID if user picked one of the Available Flights below). "
            "Map Arabic city names to English. If a field isn't mentioned, value must be null.\n\n"
            f"{avail_ctx}\n"
            f"User Message: {user_msg_content}"
        )
        try:
            res_str = await call_groq([{"role": "user", "content": extract_prompt}], model="llama-3.1-8b-instant", response_format="json_object")
            data = json.loads(res_str)
            
            raw_dest = data.get("destination")
            if raw_dest and not planner_state.get("destination"):
                normalized = ARABIC_TO_ENGLISH_CITY.get(raw_dest, raw_dest)
                planner_state["destination"] = normalized
                pending_control = "planner"

            if data.get("budget"):
                hotel_state["budget"] = float(data["budget"])

            if data.get("seat_class") and not flight_state.get("seat_class") and not flight_state.get("selected_flight"):
                flight_state["seat_class"] = data["seat_class"].lower()
                pending_control = "flight"

            if data.get("selected_program_id"):
                planner_state["selected_program_id"] = data["selected_program_id"]
                pending_control = "planner"

            if data.get("selected_hotel_id"):
                hotel_state["selected_hotel_id"] = data["selected_hotel_id"]
                pending_control = "hotel"

            if data.get("selected_flight_id"):
                flight_state["selected_flight_id"] = data["selected_flight_id"]
                pending_control = "flight"

        except Exception:
            pass

    # Save extracted state back into global state
    state["planner"] = planner_state
    state["hotel"] = hotel_state
    state["flight"] = flight_state


    # Build system prompt with language detection and full context
    selected_program = planner_state.get("selected_program")
    selected_hotel = hotel_state.get("selected_hotel")
    selected_flight = flight_state.get("selected_flight")
    booking_ref = flight_state.get("booking_reference")
    
    context_lines = []
    if planner_state.get("destination"):
        context_lines.append(f"Destination: {planner_state['destination']}")
    
    # Inject available program highlights if programs are loaded but none selected
    if planner_state.get("available_programs") and not selected_program:
        context_lines.append("Available Programs Details:")
        for p in planner_state["available_programs"]:
            context_lines.append(f"- {p['program_name']}: {p.get('highlights', 'No extra details')}")

    if selected_program:
        context_lines.append(f"Selected Program: {selected_program.get('program_name')} ({selected_program.get('days')} days, ~${selected_program.get('approx_budget_per_person')}/person)\nDetails: {selected_program.get('highlights', '')}")
    if selected_hotel:
        context_lines.append(f"Selected Hotel: {selected_hotel.get('name')} ({selected_hotel.get('stars')}★, ${selected_hotel.get('price_per_night')}/night near {selected_hotel.get('near_attraction')})")
    if selected_flight:
        context_lines.append(f"Selected Flight: {selected_flight.get('airline')} from {selected_flight.get('origin')} → ${selected_flight.get('base_price')} ({flight_state.get('seat_class')} class, {flight_state.get('baggage_kg', 20)}kg baggage)")
    if booking_ref:
        context_lines.append(f"Booking Reference: {booking_ref}")
    
    context_summary = "\n".join(context_lines) if context_lines else "No selections yet."
    
    # Logic to determine if we should show buttons based on state
    options = []
    if not planner_state.get("destination"):
        pass  # Keep it natural chat, let user type destination
    elif not planner_state.get("selected_program"):
        if not planner_state.get("available_programs"):
            options.append({"label": f"🔍 Find Programs in {planner_state['destination']}", "action": "trigger_planner", "payload": {}})
        else:
            for p in planner_state["available_programs"]:
                label = f"✈️ {p['program_name']} — {p['days']} days | {p.get('category','').replace('_',' ').title()} | ~${p.get('approx_budget_per_person','')}pp"
                options.append({
                    "label": label,
                    "action": "select_program",
                    "payload": {"program_id": p["id"]}
                })
    elif not hotel_state.get("selected_hotel"):
        if not hotel_state.get("searched"):
            options.append({"label": "🏨 Search Hotels", "action": "trigger_hotel", "payload": {}})
        elif not hotel_state.get("available_hotels"):
            options.append({"label": "⚠️ Skip Hotel (None Found)", "action": "select_hotel", "payload": {"hotel_id": "none"}})
        else:
            for h in hotel_state["available_hotels"]:
                label = f"🏨 {h['name']} — {h.get('stars','')}★ | {h.get('currency','')}{h['price_per_night']}/night | {h.get('near_attraction','')}"
                options.append({
                    "label": label,
                    "action": "select_hotel",
                    "payload": {"hotel_id": h["id"]}
                })
    elif not flight_state.get("selected_flight"):
        if not flight_state.get("searched"):
            options.append({"label": "🛫 Search Economy Flights", "action": "trigger_flight", "payload": {"seat_class": "economy"}})
            options.append({"label": "💺 Search Business Flights", "action": "trigger_flight", "payload": {"seat_class": "business"}})
        elif not flight_state.get("available_flights"):
            options.append({"label": "⚠️ Skip Flight (None Found)", "action": "select_flight", "payload": {"flight_id": "none"}})
        else:
            for f in flight_state["available_flights"]:
                label = (
                    f"✈️ {f['airline']} — {f.get('origin','')}→{f.get('destination','')} | "
                    f"{f.get('currency','')}{f['base_price']} | {f.get('seat_class','').title()} | "
                    f"{f.get('baggage_included_kg','')}kg incl. (+{f.get('extra_baggage_price_per_kg','')} per extra kg)"
                )
                options.append({
                    "label": label,
                    "action": "select_flight",
                    "payload": {"flight_id": f["id"]}
                })
    elif not flight_state.get("user_confirmed"):
        options.append({
            "label": f"✅ CONFIRM BOOKING",
            "action": "confirm_booking",
            "payload": {}
        })

    # Tell the LLM what options are currently visible to the user
    if options:
        opts_str = "\n".join([f"- {opt['label']}" for opt in options])
        context_summary += f"\n\nRight now, the user sees the following clickable options (buttons) on their screen:\n{opts_str}\n\nYou MUST NOT pretend these options are missing or haven't arrived. They ARE on the screen. Help the user choose from them."

    sys_prompt = {
        "role": "system",
        "content": (
            "You are a friendly, expert travel assistant.\n"
            "CRITICAL LANGUAGE RULE: Detect the language the user is writing in (Arabic or English) and respond ENTIRELY in that same language. Never mix languages.\n\n"
            f"Current interaction context:\n{context_summary}\n\n"
            "CRITICAL BEHAVIOR RULES - YOU MUST FOLLOW THESE EXACTLY:\n"
            "1. We ONLY support the following destinations: Barcelona, Lisbon, Porto, Athens, Santorini, Rome, Paris, Berlin, Zurich. If a user asks for anywhere else (like Cairo), politely apologize and say we only support these cities.\n"
            "2. NEVER make up itinerary, program, hotel or flight details. If the user asks about programs, use the 'Available Programs Details' above to answer naturally.\n"
            "3. If 'Destination' is missing from the status, ask the user to type where they want to go. Do NOT mention buttons or options.\n"
            "4. If options are provided below (for programs, hotels, or flights), your job is to greet the user or answer their question naturally, then encourage them to select an option.\n"
            "5. If the user typed a preference (like 'economy' or a city) instead of clicking a button, acknowledge it warmly and say we have updated their options below.\n"
            "6. You CANNOT confirm bookings via text. Selections ONLY happen when the system processes the user's choices.\n"
            "Keep responses friendly and concise. Do NOT repeat yourself."
        )
    }
    
    groq_messages = [sys_prompt] + messages

    
    full_reply = ""
    if websocket:
        # Stream response
        async for token in call_groq_streaming(groq_messages):
            full_reply += token
            await websocket.send_json({"type": "token", "content": token})
    
        if options and state.get("control") != "done":
            await websocket.send_json({"type": "action_options", "options": options})
            
        await websocket.send_json({"type": "end_of_message"})
    
    # Save the reply
    new_messages = list(messages)
    new_messages.append({"role": "assistant", "content": full_reply})
    state["messages"] = new_messages
    
    # Forward the control effectively if natural language triggered an agent (e.g. planner or flight)
    state["control"] = pending_control
    return state

