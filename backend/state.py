from typing import List, Optional, TypedDict, Literal


class PlannerState(TypedDict, total=False):
    """State owned by the travel planner agent."""

    destination: str
    itinerary: str


class HotelRecord(TypedDict):
    """Single hotel entry in the mock database."""

    id: str
    name: str
    country: str
    city: str
    stars: int
    price_per_night: float
    currency: str
    near_attraction: str


class HotelState(TypedDict, total=False):
    """State owned by the hotel booking agent."""

    budget: Optional[float]
    min_stars: Optional[int]

    # Computed / output values
    available_hotels: List[HotelRecord]
    selected_hotel_id: Optional[str]
    selected_hotel: Optional[HotelRecord]


class FlightState(TypedDict, total=False):
    """State owned by the flight reservation agent."""

    seat_class: Optional[Literal["economy", "business", "first"]]
    baggage_kg: Optional[int]
    booking_reference: Optional[str]


class TravelState(TypedDict, total=False):
    """
    Global state passed through the graph.

    Each agent is responsible only for its own sub-dict and the control flag.
    Internal reasoning stays local (not stored here).
    """

    planner: PlannerState
    hotel: HotelState
    flight: FlightState

    # Router control flag: who should act next?
    control: Literal["planner", "hotel", "flight", "done"]

