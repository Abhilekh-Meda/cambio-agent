from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from state_store import create_game, get_state, patch_state, apply_move
from agent import run_agent_move
# ---------------------

app = FastAPI(title="Cambio LLM Game Agent API")

# Enable CORS for web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== Pydantic Models =====

class CreateGameRequest(BaseModel):
    player_names: Optional[List[str]] = None

class MoveRequest(BaseModel):
    move: dict

class AgentMoveRequest(BaseModel):
    player_id: str
    apply: bool = True

# ===== API Endpoints =====

@app.get("/")
def root():
    return {
        "name": "Cambio LLM Game Agent API",
        "version": "1.0.0",
        "endpoints": {
            "POST /games": "Create new game",
            "GET /games/{game_id}": "Get game state",
            "PATCH /games/{game_id}": "Update game state",
            "POST /games/{game_id}/moves": "Submit a move",
            "POST /games/{game_id}/agent_move": "Let AI agent make a move",
            "GET /games/{game_id}/history": "Get move history"
        }
    }

@app.post("/games")
def create_game_endpoint(req: CreateGameRequest):
    """Create a new Cambio game."""
    game_id = create_game(req.player_names or ["Player1", "Player2"])
    state = get_state(game_id)
    return {
        "game_id": game_id,
        "state": state
    }

@app.get("/games/{game_id}")
def get_game_endpoint(game_id: str):
    """Get current game state."""
    state = get_state(game_id)
    if not state:
        raise HTTPException(status_code=404, detail="Game not found")
    return state

@app.patch("/games/{game_id}")
def patch_game_endpoint(game_id: str, patch: dict):
    """Patch game state (use with caution - bypasses validation)."""
    try:
        state = patch_state(game_id, patch)
        return state
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/games/{game_id}/moves")
def submit_move_endpoint(game_id: str, req: MoveRequest):
    """Submit and apply a move with validation."""
    result = apply_move(game_id, req.move)
    
    if not result.get("valid"):
        raise HTTPException(status_code=400, detail=result.get("reason"))
    
    return result

@app.post("/games/{game_id}/agent_move")
def agent_move_endpoint(game_id: str, req: AgentMoveRequest):
    """Let the LLM agent decide and execute a move."""
    state = get_state(game_id)
    if not state:
        raise HTTPException(status_code=404, detail="Game not found")
    
    result = run_agent_move(game_id, req.player_id, req.apply)
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result

@app.get("/games/{game_id}/history")
def get_history_endpoint(game_id: str):
    """Get game history."""
    state = get_state(game_id)
    if not state:
        raise HTTPException(status_code=404, detail="Game not found")
    return {"history": state.get("history", [])}


# ============================================================================
# Run the server
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    print("Starting Cambio Game Agent API...")
    print("Make sure to set OPENAI_API_KEY in your .env file")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)