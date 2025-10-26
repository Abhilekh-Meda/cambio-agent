import json
from langchain.tools import Tool
from typing import Any

def tool_get_board(game_id: str) -> str:
    """Tool to get current game state."""
    state = get_state(game_id)
    if not state:
        return json.dumps({"error": "Game not found"})
    
    # Return a simplified view for the agent
    agent_view = {
        "game_id": state["game_id"],
        "current_player": state["current_player"],
        "turn_phase": state["turn_phase"],
        "players": [],
        "top_discard": state["top_discard"],
        "draw_pile_count": state["draw_pile_count"]
    }
    
    for player in state["players"]:
        player_view = {
            "player_id": player["player_id"],
            "name": player["name"],
            "hand": []
        }
        for i, card_slot in enumerate(player["hand"]):
            if card_slot["visible"]:
                player_view["hand"].append({
                    "slot": i,
                    "card": card_slot["card"],
                    "value": get_card_value(card_slot["card"])
                })
            else:
                player_view["hand"].append({
                    "slot": i,
                    "card": "unknown",
                    "value": "?"
                })
        agent_view["players"].append(player_view)
    
    return json.dumps(agent_view, indent=2)

def tool_apply_move(payload: str) -> str:
    """Tool to apply a move. Payload is JSON: {"game_id": "...", "move": {...}}"""
    try:
        data = json.loads(payload)
        game_id = data["game_id"]
        move = data["move"]
        
        result = apply_move(game_id, move)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"valid": False, "reason": str(e)})

def create_agent_tools():
    """Create LangChain tools for the agent."""
    return [
        Tool(
            name="get_board",
            func=tool_get_board,
            description="Returns the current game state as JSON for a given game_id. Input: game_id string."
        ),
        Tool(
            name="apply_move",
            func=tool_apply_move,
            description='Apply a move to the game. Input: JSON string with format {"game_id": "...", "move": {"type": "draw_deck"|"draw_discard_swap"|"peek"|"call_cambio", "slot": 0-3}}. Returns validation result.'
        )
    ]
