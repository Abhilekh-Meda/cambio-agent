import uuid
from typing import Dict, Optional, List
from copy import deepcopy
import random

# In-memory store (use Redis/Postgres for production)
_game_store: Dict[str, dict] = {}

def create_deck() -> List[str]:
    """Create and shuffle a standard 52-card deck."""
    suits = ['H', 'D', 'C', 'S']
    ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
    deck = [f"{rank}{suit}" for suit in suits for rank in ranks]
    random.shuffle(deck)
    return deck

def get_card_value(card: str) -> int:
    """Get numeric value of a card for scoring."""
    if not card:
        return 0
    rank = card[:-1]
    if rank == 'K':
        return 0
    elif rank == 'Q':
        return 12
    elif rank == 'J':
        return 11
    elif rank == 'A':
        return 1
    return int(rank)

def create_game(player_names: List[str] = None) -> str:
    """Create a new game and return game_id."""
    if not player_names:
        player_names = ['Player1', 'Player2']
    
    game_id = str(uuid.uuid4())
    deck = create_deck()
    
    # Deal 4 cards to each player
    players = []
    idx = 0
    for i, name in enumerate(player_names):
        hand = [
            {"card": deck[idx], "visible": False},
            {"card": deck[idx+1], "visible": False},
            {"card": deck[idx+2], "visible": False},
            {"card": deck[idx+3], "visible": False}
        ]
        # Peek at 2 cards initially (game rule)
        hand[0]["visible"] = True
        hand[2]["visible"] = True
        
        players.append({
            "player_id": f"p{i+1}",
            "name": name,
            "seat": i,
            "hand": hand,
            "score": 0
        })
        idx += 4
    
    state = {
        "game_id": game_id,
        "variant": "cambio_standard",
        "players": players,
        "draw_pile": deck[idx:],
        "draw_pile_count": len(deck[idx:]),
        "top_discard": None,
        "current_player": "p1",
        "turn_phase": "awaiting_action",
        "history": [],
        "metadata": {
            "started_at": "2025-10-25T08:00:00Z",
            "round": 1
        }
    }
    
    _game_store[game_id] = state
    return game_id

def get_state(game_id: str) -> Optional[dict]:
    """Retrieve game state."""
    return deepcopy(_game_store.get(game_id))

def patch_state(game_id: str, patch: dict) -> dict:
    """Update game state with patch."""
    if game_id not in _game_store:
        raise ValueError(f"Game {game_id} not found")
    
    state = _game_store[game_id]
    state.update(patch)
    return deepcopy(state)

def validate_move(game_id: str, move: dict) -> tuple[bool, Optional[str]]:
    """Validate if a move is legal."""
    state = _game_store.get(game_id)
    if not state:
        return False, "Game not found"
    
    if state["turn_phase"] == "round_end":
        return False, "Round has ended"
    
    move_type = move.get("type")
    
    if move_type == "draw_deck":
        if state["draw_pile_count"] == 0:
            return False, "Draw pile is empty"
        return True, None
    
    elif move_type == "draw_discard_swap":
        if not state["top_discard"]:
            return False, "No card in discard pile"
        slot = move.get("slot")
        if slot is None or slot < 0 or slot > 3:
            return False, "Invalid slot"
        return True, None
    
    elif move_type == "peek":
        slot = move.get("slot")
        if slot is None or slot < 0 or slot > 3:
            return False, "Invalid slot"
        return True, None
    
    elif move_type == "call_cambio":
        return True, None
    
    return False, f"Unknown move type: {move_type}"

def apply_move(game_id: str, move: dict) -> dict:
    """Apply a validated move and return result."""
    valid, reason = validate_move(game_id, move)
    if not valid:
        return {"valid": False, "reason": reason}
    
    state = _game_store[game_id]
    current_player = next(p for p in state["players"] if p["player_id"] == state["current_player"])
    
    move_type = move["type"]
    
    if move_type == "draw_deck":
        drawn = state["draw_pile"].pop(0)
        state["draw_pile_count"] = len(state["draw_pile"])
        state["top_discard"] = drawn
        state["history"].append({
            "turn": len(state["history"]) + 1,
            "player": state["current_player"],
            "action": f"drew from deck"
        })
    
    elif move_type == "draw_discard_swap":
        slot = move["slot"]
        old_card = current_player["hand"][slot]["card"]
        current_player["hand"][slot] = {"card": state["top_discard"], "visible": True}
        state["top_discard"] = old_card
        state["history"].append({
            "turn": len(state["history"]) + 1,
            "player": state["current_player"],
            "action": f"drew from discard and swapped slot {slot}"
        })
    
    elif move_type == "peek":
        slot = move["slot"]
        current_player["hand"][slot]["visible"] = True
        state["history"].append({
            "turn": len(state["history"]) + 1,
            "player": state["current_player"],
            "action": f"peeked at slot {slot}"
        })
    
    elif move_type == "call_cambio":
        # Reveal all cards and calculate scores
        for player in state["players"]:
            for card_slot in player["hand"]:
                card_slot["visible"] = True
            player["score"] = sum(get_card_value(c["card"]) for c in player["hand"])
        
        state["turn_phase"] = "round_end"
        state["history"].append({
            "turn": len(state["history"]) + 1,
            "player": state["current_player"],
            "action": "called Cambio!"
        })
        return {"valid": True, "state": deepcopy(state), "round_end": True}
    
    # Switch to next player
    current_idx = state["players"].index(current_player)
    next_idx = (current_idx + 1) % len(state["players"])
    state["current_player"] = state["players"][next_idx]["player_id"]
    
    return {"valid": True, "state": deepcopy(state)}
import uuid
from typing import Dict, Optional, List
from copy import deepcopy
import random

# In-memory store (use Redis/Postgres for production)
_game_store: Dict[str, dict] = {}

def create_deck() -> List[str]:
    """Create and shuffle a standard 52-card deck."""
    suits = ['H', 'D', 'C', 'S']
    ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
    deck = [f"{rank}{suit}" for suit in suits for rank in ranks]
    random.shuffle(deck)
    return deck

def get_card_value(card: str) -> int:
    """Get numeric value of a card for scoring."""
    if not card:
        return 0
    rank = card[:-1]
    if rank == 'K':
        return 0
    elif rank == 'Q':
        return 12
    elif rank == 'J':
        return 11
    elif rank == 'A':
        return 1
    return int(rank)

def create_game(player_names: List[str] = None) -> str:
    """Create a new game and return game_id."""
    if not player_names:
        player_names = ['Player1', 'Player2']
    
    game_id = str(uuid.uuid4())
    deck = create_deck()
    
    # Deal 4 cards to each player
    players = []
    idx = 0
    for i, name in enumerate(player_names):
        hand = [
            {"card": deck[idx], "visible": False},
            {"card": deck[idx+1], "visible": False},
            {"card": deck[idx+2], "visible": False},
            {"card": deck[idx+3], "visible": False}
        ]
        # Peek at 2 cards initially (game rule)
        hand[0]["visible"] = True
        hand[2]["visible"] = True
        
        players.append({
            "player_id": f"p{i+1}",
            "name": name,
            "seat": i,
            "hand": hand,
            "score": 0
        })
        idx += 4
    
    state = {
        "game_id": game_id,
        "variant": "cambio_standard",
        "players": players,
        "draw_pile": deck[idx:],
        "draw_pile_count": len(deck[idx:]),
        "top_discard": None,
        "current_player": "p1",
        "turn_phase": "awaiting_action",
        "history": [],
        "metadata": {
            "started_at": "2025-10-25T08:00:00Z",
            "round": 1
        }
    }
    
    _game_store[game_id] = state
    return game_id

def get_state(game_id: str) -> Optional[dict]:
    """Retrieve game state."""
    return deepcopy(_game_store.get(game_id))

def patch_state(game_id: str, patch: dict) -> dict:
    """Update game state with patch."""
    if game_id not in _game_store:
        raise ValueError(f"Game {game_id} not found")
    
    state = _game_store[game_id]
    state.update(patch)
    return deepcopy(state)

def validate_move(game_id: str, move: dict) -> tuple[bool, Optional[str]]:
    """Validate if a move is legal."""
    state = _game_store.get(game_id)
    if not state:
        return False, "Game not found"
    
    if state["turn_phase"] == "round_end":
        return False, "Round has ended"
    
    move_type = move.get("type")
    
    if move_type == "draw_deck":
        if state["draw_pile_count"] == 0:
            return False, "Draw pile is empty"
        return True, None
    
    elif move_type == "draw_discard_swap":
        if not state["top_discard"]:
            return False, "No card in discard pile"
        slot = move.get("slot")
        if slot is None or slot < 0 or slot > 3:
            return False, "Invalid slot"
        return True, None
    
    elif move_type == "peek":
        slot = move.get("slot")
        if slot is None or slot < 0 or slot > 3:
            return False, "Invalid slot"
        return True, None
    
    elif move_type == "call_cambio":
        return True, None
    
    return False, f"Unknown move type: {move_type}"

def apply_move(game_id: str, move: dict) -> dict:
    """Apply a validated move and return result."""
    valid, reason = validate_move(game_id, move)
    if not valid:
        return {"valid": False, "reason": reason}
    
    state = _game_store[game_id]
    current_player = next(p for p in state["players"] if p["player_id"] == state["current_player"])
    
    move_type = move["type"]
    
    if move_type == "draw_deck":
        drawn = state["draw_pile"].pop(0)
        state["draw_pile_count"] = len(state["draw_pile"])
        state["top_discard"] = drawn
        state["history"].append({
            "turn": len(state["history"]) + 1,
            "player": state["current_player"],
            "action": f"drew from deck"
        })
    
    elif move_type == "draw_discard_swap":
        slot = move["slot"]
        old_card = current_player["hand"][slot]["card"]
        current_player["hand"][slot] = {"card": state["top_discard"], "visible": True}
        state["top_discard"] = old_card
        state["history"].append({
            "turn": len(state["history"]) + 1,
            "player": state["current_player"],
            "action": f"drew from discard and swapped slot {slot}"
        })
    
    elif move_type == "peek":
        slot = move["slot"]
        current_player["hand"][slot]["visible"] = True
        state["history"].append({
            "turn": len(state["history"]) + 1,
            "player": state["current_player"],
            "action": f"peeked at slot {slot}"
        })
    
    elif move_type == "call_cambio":
        # Reveal all cards and calculate scores
        for player in state["players"]:
            for card_slot in player["hand"]:
                card_slot["visible"] = True
            player["score"] = sum(get_card_value(c["card"]) for c in player["hand"])
        
        state["turn_phase"] = "round_end"
        state["history"].append({
            "turn": len(state["history"]) + 1,
            "player": state["current_player"],
            "action": "called Cambio!"
        })
        return {"valid": True, "state": deepcopy(state), "round_end": True}
    
    # Switch to next player
    current_idx = state["players"].index(current_player)
    next_idx = (current_idx + 1) % len(state["players"])
    state["current_player"] = state["players"][next_idx]["player_id"]
    
    return {"valid": True, "state": deepcopy(state)}
