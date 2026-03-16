from typing import List, Optional, TypedDict, Literal, Dict


class Message(TypedDict):
    role: Literal["user", "assistant", "system"]
    content: str


class PlannerState(TypedDict, total=False):
    """State owned by the travel planner agent."""

    destination: str
    available_programs: List[Dict]
    selected_program_id: Optional[str]
    selected_program: Optional[Dict]
    itinerary: str
    approx_budget_per_person: Optional[float]


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
    
    available_flights: List[Dict]
    selected_flight_id: Optional[str]
    selected_flight: Optional[Dict]
    
    user_confirmed: Optional[bool]
    booking_confirmation: Optional[str]
    booking_reference: Optional[str]


class TravelState(TypedDict, total=False):
    """
    Global state passed through the graph.

    Each agent is responsible only for its own sub-dict and the control flag.
    Internal reasoning stays local (not stored here).
    """

    messages: List[Message]          # full history – only conversation agent reads
    summary: str                     # condensed conversation for LLM context

    planner: PlannerState
    hotel: HotelState
    flight: FlightState

    # Router control flag: who should act next?
    control: Literal["conversation", "planner", "hotel", "flight", "done"]

    user_name: Optional[str]
    user_email: Optional[str]
