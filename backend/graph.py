from __future__ import annotations

from typing import Literal

from langgraph.graph import END, START, StateGraph

from nodes import (
    flight_reservation_agent,
    hotel_booking_agent,
    travel_planner_agent,
)
from state import TravelState


def control_router(
    state: TravelState,
) -> Literal["travel_planner", "hotel_booking", "flight_reservation", "__end__"]:
    """
    Router that performs strict hand-off based on ``state["control"]``.

    It does not inspect or modify agent-local state beyond this flag.
    """
    control = state.get("control")

    if control == "planner":
        return "travel_planner"
    if control == "hotel":
        return "hotel_booking"
    if control == "flight":
        return "flight_reservation"
    if control == "done":
        return "__end__"

    # Default to planner if not initialized.
    return "travel_planner"


def build_travel_graph():
    """Construct and compile the multi-agent travel graph."""
    builder: StateGraph[TravelState] = StateGraph(TravelState)

    # Core agent nodes.
    builder.add_node("travel_planner", travel_planner_agent)
    builder.add_node("hotel_booking", hotel_booking_agent)
    builder.add_node("flight_reservation", flight_reservation_agent)

    # Router edges starting from START, using the control flag.
    builder.add_conditional_edges(
        START,
        control_router,
        {
            "travel_planner": "travel_planner",
            "hotel_booking": "hotel_booking",
            "flight_reservation": "flight_reservation",
            "__end__": END,
        },
    )

    # After each agent finishes, return to START so the router can decide.
    builder.add_edge("travel_planner", START)
    builder.add_edge("hotel_booking", START)
    builder.add_edge("flight_reservation", START)

    graph = builder.compile()
    return graph


if __name__ == "__main__":
    """
    Example of how you might drive the graph.

    In a real app, you would:
      1) Initialize with control="planner" and planner.destination from the user.
      2) Run until control=="hotel" with ``available_hotels``, present them,
         set ``selected_hotel_id``, then run again.
      3) Collect flight preferences, set ``flight.seat_class`` and
         ``flight.baggage_kg``, then run until control=="done".
    """
    graph = build_travel_graph()

    # Example single-shot invocation (all decisions pre-specified).
    initial_state: TravelState = {
        "control": "planner",
        "planner": {"destination": "Barcelona"},
        "hotel": {
            "budget": 350.0,
            "sea_view": True,
            "min_stars": 4,
            "selected_hotel_id": "H1",
        },
        "flight": {
            "seat_class": "economy",
            "baggage_kg": 23,
        },
    }

    final_state = graph.invoke(initial_state)
    print("Itinerary:\n", final_state["planner"]["itinerary"])
    print("Hotel:", final_state["hotel"]["selected_hotel"])
    print("Flight booking reference:", final_state["flight"]["booking_reference"])

