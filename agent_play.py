import os
import json
import re
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from agent_tools import create_agent_tools # <-- ADDED IMPORTS
from state_store import apply_move   # <-- ADDED IMPORTS

load_dotenv()

# Agent prompt template
CAMBIO_AGENT_PROMPT = """You are an expert Cambio card game player. You must analyze the game state and choose the best legal move.

GAME RULES:
- Each player has 4 cards (slots 0-3)
- Goal: Get the lowest total card value
- Card values: K=0, A=1, 2-10=face value, J=11, Q=12
- You can: draw from deck, swap with discard, peek at unknown cards, or call Cambio to end the round
- Only call Cambio when you believe you have the lowest score

STRATEGY TIPS:
- Peek at unknown cards first to gather information
- Swap high-value cards (8+) with lower discard cards
- Call Cambio when your visible cards suggest you have a low total
- Kings (value 0) are the best cards to keep

You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: a JSON object with "move" and "explain" keys

Begin!

Question: {input}
Thought: {agent_scratchpad}"""

def create_cambio_agent():
    """Create the LangChain agent for playing Cambio."""
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.1,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    tools = create_agent_tools()
    prompt = PromptTemplate.from_template(CAMBIO_AGENT_PROMPT)
    agent = create_react_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        max_iterations=5,
        handle_parsing_errors=True
    )
    
    return agent_executor

def run_agent_move(game_id: str, player_id: str, apply: bool = True) -> dict:
    """Run the agent to decide and optionally apply a move."""
    try:
        agent = create_cambio_agent()
        
        question = f"""
Game ID: {game_id}
Player ID: {player_id}

Task: Analyze the current game state and propose ONE legal move for player {player_id}.

Steps:
1. Use get_board tool to see the current state
2. Analyze which cards you can see and their values
3. Choose the best move based on the strategy
4. Output ONLY valid JSON with this exact format:
{{"move": {{"type": "...", "slot": ...}}, "explain": "brief reason"}}

Valid move types:
- {{"type": "peek", "slot": 0-3}} - look at an unknown card
- {{"type": "draw_deck"}} - draw from deck
- {{"type": "draw_discard_swap", "slot": 0-3}} - take discard and swap with your card
- {{"type": "call_cambio"}} - end the round (use when confident you have lowest score)
"""
        
        result = agent.invoke({"input": question})
        output = result.get("output", "{}")
        
        # Parse the agent's output
        try:
            decision = json.loads(output)
        except json.JSONDecodeError:
            json_match = re.search(r'\{.*\}', output, re.DOTALL)
            if json_match:
                decision = json.loads(json_match.group())
            else:
                return {"error": "Agent failed to produce valid JSON", "raw_output": output}
        
        if apply:
            move_result = apply_move(game_id, decision["move"])
            decision["applied"] = move_result.get("valid", False)
            if not move_result.get("valid"):
                decision["error"] = move_result.get("reason")
        
        return decision
        
    except Exception as e:
        return {"error": str(e)}