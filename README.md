# AI Travel Agent: Agentic Workflow via LangGraph ✈️

A production-ready travel booking system designed as a technical interview demonstration. It leverages **LangGraph-inspired** orchestration for complex, multi-step agentic workflows, integrated with a **FastAPI** backend, **Supabase** for persistence, and a modern **React + Vite** frontend.

## 🧠 Agentic Architecture (LangGraph Implementation)

This project implements a directed computational graph to handle the non-linear nature of travel planning. Unlike traditional linear flows, the system uses an agentic state-machine approach:

- **State Management**: A centralized `TravelState` object tracks the itinerary, selected accommodations, flight preferences, and workflow control tokens across all nodes.
- **Node-based Orchestration**:
  - **Planner Node**: Analyzes travel programs and initializes the itinerary.
  - **Hotel Node**: Handles dynamic filtering and multi-stage selection logic.
  - **Flight Node**: Orchestrates final reservations and data persistence.
- **Dynamic Control Flow**: Transitions between nodes are determined dynamically by state variables, allowing the graph to cycle back to previous states (e.g., re-evaluating hotels) based on user interaction.

## 📁 Project Structure

```text
.
├── backend/            # Python API & LangGraph Orchestration
│   ├── api.py          # RESTful endpoints (FastAPI)
│   ├── nodes.py        # Graph nodes and state transitions
│   ├── state.py        # Centralized state definitions
│   ├── supabase_client.py # Database abstraction layer
│   └── data/           # CSV data backups
├── frontend/           # React + Vite (SPA)
│   ├── src/            # Components, Hooks, and State management
│   └── package.json    # Frontend dependency tree
├── README.md           # Documentation
└── .gitignore          # Repository security & optimization
```

## 🛠️ Tech Stack
- **Backend**: FastAPI, LangGraph context, Pydantic.
- **Database**: Supabase (PostgreSQL) with RLS (Row Level Security).
- **Frontend**: React, TypeScript, Vite, Vanilla CSS.
- **State Orchestration**: Python dictionaries mimicking LangGraph state schemas.

## 🚀 Getting Started

### 1. Backend Setup
1. `cd backend`
2. `python -m venv venv`
3. `source venv/bin/activate`
4. `pip install -r requirements.txt`
5. Map your `SUPABASE_URL` and `SUPABASE_ANON_KEY` in `.env`.
6. `uvicorn api:app --reload`

### 2. Frontend Setup
1. `cd frontend`
2. `npm install`
3. `npm run dev`

---
**Developed by Ahmed Hamdy**
