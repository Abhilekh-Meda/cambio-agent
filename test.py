# test_cambio.py - Comprehensive test suite

import pytest
import json
from state_store import (
    create_game, get_state, apply_move, validate_move, get_card_value
)

class TestGameCreation:
    """Test game initialization."""
    
    def test_create_game_default(self):
        game_id = create_game()
        assert game_id is not None
        state = get_state(game_id)
        assert state["game_id"] == game_id
        assert len(state["players"]) == 2
        assert state["current_player"] == "p1"
        
    def test_initial_hand_structure(self):
        game_id = create_game()
        state = get_state(game_id)
        
        for player in state["players"]:
            assert len(player["hand"]) == 4
            # Players should see 2 cards initially (slots 0 and 2)
            assert player["hand"][0]["visible"] == True
            assert player["hand"][1]["visible"] == False
            assert player["hand"][2]["visible"] == True
            assert player["hand"][3]["visible"] == False
    
    def test_deck_distribution(self):
        game_id = create_game()
        state = get_state(game_id)
        
        # 52 cards total - 8 dealt (4 per player) = 44 remaining
        assert state["draw_pile_count"] == 44


class TestCardValues:
    """Test card value calculations."""
    
    def test_king_value(self):
        assert get_card_value("KH") == 0
        assert get_card_value("KD") == 0
        
    def test_ace_value(self):
        assert get_card_value("AH") == 1
        
    def test_number_values(self):
        assert get_card_value("2H") == 2
        assert get_card_value("7S") == 7
        assert get_card_value("10D") == 10
        
    def test_face_values(self):
        assert get_card_value("JH") == 11
        assert get_card_value("QS") == 12


class TestMoveValidation:
    """Test move validation logic."""
    
    def test_valid_draw_deck(self):
        game_id = create_game()
        valid, reason = validate_move(game_id, {"type": "draw_deck"})
        assert valid == True
        assert reason is None
        
    def test_invalid_draw_empty_pile(self):
        game_id = create_game()
        state = get_state(game_id)
        # Empty the draw pile
        state["draw_pile"] = []
        state["draw_pile_count"] = 0
        from state_store import _game_store
        _game_store[game_id] = state
        
        valid, reason = validate_move(game_id, {"type": "draw_deck"})
        assert valid == False
        assert "empty" in reason.lower()
    
    def test_valid_peek(self):
        game_id = create_game()
        valid, reason = validate_move(game_id, {"type": "peek", "slot": 1})
        assert valid == True
        
    def test_invalid_peek_slot(self):
        game_id = create_game()
        valid, reason = validate_move(game_id, {"type": "peek", "slot": 5})
        assert valid == False
        assert "slot" in reason.lower()
    
    def test_call_cambio_valid(self):
        game_id = create_game()
        valid, reason = validate_move(game_id, {"type": "call_cambio"})
        assert valid == True


class TestMoveApplication:
    """Test applying moves to game state."""
    
    def test_draw_deck_move(self):
        game_id = create_game()
        initial_state = get_state(game_id)
        initial_count = initial_state["draw_pile_count"]
        
        result = apply_move(game_id, {"type": "draw_deck"})
        
        assert result["valid"] == True
        new_state = result["state"]
        assert new_state["draw_pile_count"] == initial_count - 1
        assert new_state["top_discard"] is not None
        assert len(new_state["history"]) == 1
    
    def test_peek_move(self):
        game_id = create_game()
        initial_state = get_state(game_id)
        
        # Peek at slot 1 (initially hidden)
        result = apply_move(game_id, {"type": "peek", "slot": 1})
        
        assert result["valid"] == True
        new_state = result["state"]
        player = next(p for p in new_state["players"] if p["player_id"] == "p1")
        assert player["hand"][1]["visible"] == True
    
    def test_discard_swap_move(self):
        game_id = create_game()
        
        # First draw to populate discard
        apply_move(game_id, {"type": "draw_deck"})
        state = get_state(game_id)
        discard_card = state["top_discard"]
        
        # Now swap with slot 0
        current_player = state["current_player"]
        result = apply_move(game_id, {"type": "draw_discard_swap", "slot": 0})
        
        assert result["valid"] == True
        new_state = result["state"]
        player = next(p for p in new_state["players"] if p["player_id"] == current_player)
        assert player["hand"][0]["card"] == discard_card
        assert player["hand"][0]["visible"] == True
    
    def test_call_cambio_ends_round(self):
        game_id = create_game()
        
        result = apply_move(game_id, {"type": "call_cambio"})
        
        assert result["valid"] == True
        assert result.get("round_end") == True
        
        new_state = result["state"]
        assert new_state["turn_phase"] == "round_end"
        
        # All cards should be visible
        for player in new_state["players"]:
            for card_slot in player["hand"]:
                assert card_slot["visible"] == True
            # Score should be calculated
            assert player["score"] >= 0
    
    def test_player_turn_switches(self):
        game_id = create_game()
        initial_state = get_state(game_id)
        assert initial_state["current_player"] == "p1"
        
        result = apply_move(game_id, {"type": "draw_deck"})
        new_state = result["state"]
        assert new_state["current_player"] == "p2"
        
        result2 = apply_move(game_id, {"type": "draw_deck"})
        new_state2 = result2["state"]
        assert new_state2["current_player"] == "p1"


class TestGameFlow:
    """Integration tests for complete game flows."""
    
    def test_complete_game_round(self):
        game_id = create_game()
        
        # Player 1: draw from deck
        r1 = apply_move(game_id, {"type": "draw_deck"})
        assert r1["valid"] == True
        
        # Player 2: peek at unknown card
        r2 = apply_move(game_id, {"type": "peek", "slot": 1})
        assert r2["valid"] == True
        
        # Player 1: draw from deck again
        r3 = apply_move(game_id, {"type": "draw_deck"})
        assert r3["valid"] == True
        
        # Player 2: call Cambio
        r4 = apply_move(game_id, {"type": "call_cambio"})
        assert r4["valid"] == True
        assert r4.get("round_end") == True
        
        final_state = r4["state"]
        assert final_state["turn_phase"] == "round_end"
        
        # Verify winner is determined
        winner = min(final_state["players"], key=lambda p: p["score"])
        assert winner["score"] >= 0


# ============================================================================
# API Integration Tests (requires running server)
# ============================================================================

import requests

BASE_URL = "http://localhost:8000"

class TestAPIEndpoints:
    """Test FastAPI endpoints (requires server running)."""
    
    @pytest.fixture
    def game_id(self):
        """Create a game for testing."""
        response = requests.post(f"{BASE_URL}/games", json={})
        assert response.status_code == 200
        return response.json()["game_id"]
    
    def test_create_game_api(self):
        response = requests.post(
            f"{BASE_URL}/games",
            json={"player_names": ["Alice", "Bob"]}
        )
        assert response.status_code == 200
        data = response.json()
        assert "game_id" in data
        assert "state" in data
    
    def test_get_game_api(self, game_id):
        response = requests.get(f"{BASE_URL}/games/{game_id}")
        assert response.status_code == 200
        state = response.json()
        assert state["game_id"] == game_id
    
    def test_submit_move_api(self, game_id):
        response = requests.post(
            f"{BASE_URL}/games/{game_id}/moves",
            json={"move": {"type": "draw_deck"}}
        )
        assert response.status_code == 200
        result = response.json()
        assert result["valid"] == True
    
    def test_invalid_move_api(self, game_id):
        response = requests.post(
            f"{BASE_URL}/games/{game_id}/moves",
            json={"move": {"type": "invalid_move"}}
        )
        assert response.status_code == 400
    
    def test_agent_move_api(self, game_id):
        response = requests.post(
            f"{BASE_URL}/games/{game_id}/agent_move",
            json={"player_id": "p1", "apply": True}
        )
        # May fail if OpenAI API key not set
        if response.status_code == 200:
            data = response.json()
            assert "move" in data
            assert "explain" in data


# ============================================================================
# Usage Examples & Documentation
# ============================================================================

def example_usage():
    """
    SETUP:
    1. Install dependencies:
       pip install fastapi uvicorn langchain langchain-openai pydantic python-dotenv
    
    2. Create .env file with:
       OPENAI_API_KEY=your_key_here
    
    3. Run server:
       python main.py
    
    4. Server runs at http://localhost:8000
    """
    
    print("=== Cambio Game Agent - Usage Examples ===\n")
    
    # Example 1: Create a game programmatically
    print("1. Create a game:")
    game_id = create_game(["Alice", "Bob"])
    print(f"   Game ID: {game_id}")
    
    # Example 2: View game state
    print("\n2. View game state:")
    state = get_state(game_id)
    print(f"   Current player: {state['current_player']}")
    print(f"   Draw pile: {state['draw_pile_count']} cards")
    
    # Example 3: Make moves
    print("\n3. Player 1 draws from deck:")
    result = apply_move(game_id, {"type": "draw_deck"})
    print(f"   Valid: {result['valid']}")
    print(f"   Top discard: {result['state']['top_discard']}")
    
    print("\n4. Player 2 peeks at slot 1:")
    result = apply_move(game_id, {"type": "peek", "slot": 1})
    print(f"   Valid: {result['valid']}")
    
    # Example 4: API usage
    print("\n5. API Usage Examples:")
    print("""
    # Create game
    POST http://localhost:8000/games
    Body: {"player_names": ["Alice", "Bob"]}
    
    # Get game state
    GET http://localhost:8000/games/{game_id}
    
    # Submit move
    POST http://localhost:8000/games/{game_id}/moves
    Body: {"move": {"type": "draw_deck"}}
    
    # Let AI make a move
    POST http://localhost:8000/games/{game_id}/agent_move
    Body: {"player_id": "p2", "apply": true}
    """)


if __name__ == "__main__":
    # Run example usage
    example_usage()
    
    # Run tests with pytest
    print("\n\nTo run tests:")
    print("  pytest test_cambio.py -v")