from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()


def get_supabase() -> Client:
    """
    Return a Supabase client using environment variables.

    Required env vars:
      - SUPABASE_URL
      - SUPABASE_ANON_KEY
    """
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_ANON_KEY must be set in the environment.",
        )
    return create_client(url, key)


def get_travel_programs_for_city(city: str) -> List[Dict[str, Any]]:
    """
    Fetch all travel programs for a given city.
    """
    supabase = get_supabase()
    res = (
        supabase.table("travel_programs")
        .select("*")
        .eq("city", city)
        .execute()
    )
    return res.data or []


def get_hotels_for_city(city: str) -> List[Dict[str, Any]]:
    """Fetch all hotels for a given city."""
    supabase = get_supabase()
    res = (
        supabase.table("hotels")
        .select("*")
        .eq("city", city)
        .execute()
    )
    return res.data or []


def get_flights_for_destination(destination_code: str, seat_class: str) -> List[Dict[str, Any]]:
    """
    Fetch flights for a given destination airport code and seat class.
    """
    supabase = get_supabase()
    res = (
        supabase.table("flights")
        .select("*")
        .eq("destination", destination_code)
        .eq("seat_class", seat_class)
        .execute()
    )
    return res.data or []


def insert_booking(row: Dict[str, Any]) -> None:
    """Insert a booking confirmation row into the bookings table."""
    supabase = get_supabase()
    supabase.table("bookings").insert(row).execute()

