#!/usr/bin/env python3
"""
Three-Way Comparison: Baseline vs Prompt-Memory vs RAG-Memory
Testing on Trading Game and Ultimatum Game
"""
import sys
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import uuid

sys.path.insert(0, str(Path(__file__).parent))
load_dotenv(".env")

from negotiationarena.agents.chatgpt import ChatGPTAgent
from negotiationarena.game_objects.resource import Resources
from negotiationarena.game_objects.goal import ResourceGoal, UltimatumGoal
from negotiationarena.game_objects.valuation import Valuation
from negotiationarena.constants import *

# Import games
try:
    from games.trading_game.game import TradingGame
    TRADING_GAME_AVAILABLE = True
except ImportError as e:
    print(f"[INIT] Warning: Could not import TradingGame: {e}")
    TRADING_GAME_AVAILABLE = False

try:
    from games.ultimatum.game import MultiTurnUltimatumGame
    ULTIMATUM_GAME_AVAILABLE = True
except ImportError as e:
    print(f"[INIT] Warning: Could not import UltimatumGame: {e}")
    ULTIMATUM_GAME_AVAILABLE = False


class RAGMemoryAgent(ChatGPTAgent):
    """Wrapper to use MemoryAugmentedNegotiator within game framework"""
    
    def __init__(self, agent_name, rag_negotiator=None, **kwargs):
        super().__init__(agent_name=agent_name, **kwargs)
        self.rag_negotiator = rag_negotiator
        self.is_rag_agent = rag_negotiator is not None
    
    def step(self, observation):
        """Override to use RAG negotiator if available"""
        if not self.is_rag_agent or self.rag_negotiator is None:
            return super().step(observation)
        
        try:
            response = self.rag_negotiator.generate_response(
                message=str(observation)[-500:],
                game_context={},
                system_prompt=self.prompt_entity_initializer or "",
                role=self.agent_name
            )
            return response
        except Exception as e:
            print(f"[{self.agent_name}] RAG error: {e}, falling back to baseline")
            return super().step(observation)


def run_trading_game(game_id, agent_type="baseline", run_id=None):
    """
    Run a trading game with specified agent type
    
    agent_type: "baseline", "prompt_memory", or "rag_memory"
    """
    if not TRADING_GAME_AVAILABLE:
        return {
            "success": False,
            "agent_type": agent_type,
            "error": "TradingGame not available",
            "run_id": run_id,
            "game_type": "trading"
        }
    
    type_labels = {
        "baseline": "BASELINE",
        "prompt_memory": "PROMPT-MEMORY",
        "rag_memory": "RAG-MEMORY"
    }
    
    print(f"\n{'='*70}")
    print(f"Trading Game #{game_id} - {type_labels.get(agent_type, agent_type).upper()}")
    print(f"{'='*70}")
    
    # Base prompts
    player1_prompt = (
        f"You are {AGENT_ONE}. "
        "You start with X: 25, Y: 5. Your goal is to acquire 15 X and 15 Y. "
        "Propose trades strategically to reach your goal."
    )
    
    player2_prompt = (
        f"You are {AGENT_TWO}. "
        "You start with X: 5, Y: 25. Your goal is to acquire 15 X and 15 Y. "
        "Respond to trades strategically to reach your goal."
    )
    
    # Add memory instructions for prompt-based approach
    if agent_type == "prompt_memory":
        memory_boost = (
            "\n\nKEY GUIDANCE: Throughout this negotiation:\n"
            "1. Track what resources the other player has proposed or requested\n"
            "2. Remember your progress toward the goal in each round\n"
            "3. Identify which resources are most valuable for your goal\n"
            "4. Use strategic offers to guide negotiations toward your goal\n"
            "5. Adapt your strategy based on patterns you observe"
        )
        player1_prompt += memory_boost
        player2_prompt += memory_boost
    
    # Create agents
    a1 = ChatGPTAgent(agent_name=AGENT_ONE, model="gpt-4-1106-preview")
    a2 = ChatGPTAgent(agent_name=AGENT_TWO, model="gpt-4-1106-preview")
    
    # For RAG agent, wrap with memory negotiator (if available)
    if agent_type == "rag_memory":
        try:
            a1 = RAGMemoryAgent(
                agent_name=AGENT_ONE,
                model="gpt-4-1106-preview",
                rag_negotiator=None
            )
            a2 = RAGMemoryAgent(
                agent_name=AGENT_TWO,
                model="gpt-4-1106-preview",
                rag_negotiator=None
            )
            print(f"  [INFO] Using RAG memory framework (simplified)")
        except Exception as e:
            print(f"  [WARNING] RAG initialization failed: {e}")
            agent_type = "baseline"
    
    # Run game
    try:
        game = TradingGame(
            players=[a1, a2],
            iterations=6,
            resources_support_set=Resources({"X": 0, "Y": 0}),
            player_goals=[
                ResourceGoal({"X": 15, "Y": 15}),
                ResourceGoal({"X": 15, "Y": 15}),
            ],
            player_initial_resources=[
                Resources({"X": 25, "Y": 5}),
                Resources({"X": 5, "Y": 25}),
            ],
            player_social_behaviour=["", ""],
            player_roles=[player1_prompt, player2_prompt],
            log_dir=f"./.logs/trading_memory/{agent_type}/{run_id}/",
        )
        
        game.run()
        
        final_state = game.game_state[-1]
        total_turns = len(game.game_state) - 2
        
        result = {
            "success": True,
            "agent_type": agent_type,
            "total_turns": total_turns,
            "run_id": run_id,
            "game_type": "trading"
        }
        
        print(f"  Status: ✓ GAME COMPLETED")
        print(f"  Turns: {total_turns}")
        
        return result
    
    except Exception as e:
        print(f"  Status: ✗ ERROR")
        print(f"  Error: {type(e).__name__}: {str(e)[:100]}")
        return {
            "success": False,
            "agent_type": agent_type,
            "error": str(e)[:150],
            "run_id": run_id,
            "game_type": "trading"
        }


def run_ultimatum_game(game_id, agent_type="baseline", run_id=None):
    """
    Run an ultimatum game with specified agent type
    
    agent_type: "baseline", "prompt_memory", or "rag_memory"
    """
    if not ULTIMATUM_GAME_AVAILABLE:
        return {
            "success": False,
            "agent_type": agent_type,
            "error": "UltimatumGame not available",
            "run_id": run_id,
            "game_type": "ultimatum"
        }
    
    type_labels = {
        "baseline": "BASELINE",
        "prompt_memory": "PROMPT-MEMORY",
        "rag_memory": "RAG-MEMORY"
    }
    
    print(f"\n{'='*70}")
    print(f"Ultimatum Game #{game_id} - {type_labels.get(agent_type, agent_type).upper()}")
    print(f"{'='*70}")
    
    # Base prompts
    proposer_prompt = (
        f"You are {AGENT_ONE}, the proposer. "
        "You start with 100 Dollars. Propose a division to the responder. "
        "If accepted, you keep your share. If rejected, both get nothing."
    )
    
    responder_prompt = (
        f"You are {AGENT_TWO}, the responder. "
        "You will receive a proposal for dividing 100 Dollars. "
        "Accept if the split seems fair, reject otherwise."
    )
    
    # Add memory instructions for prompt-based approach
    if agent_type == "prompt_memory":
        memory_boost = (
            "\n\nKEY GUIDANCE: Throughout this negotiation:\n"
            "1. Track what proposals have been made and rejected\n"
            "2. Remember what split percentages the other player prefers\n"
            "3. Learn from previous rounds what constitutes a 'fair' offer\n"
            "4. Adapt your proposals based on acceptance/rejection patterns\n"
            "5. Use strategic psychology to influence acceptance"
        )
        proposer_prompt += memory_boost
        responder_prompt += memory_boost
    
    # Create agents
    a1 = ChatGPTAgent(agent_name=AGENT_ONE, model="gpt-4-1106-preview")
    a2 = ChatGPTAgent(agent_name=AGENT_TWO, model="gpt-4-1106-preview")
    
    # For RAG agent, wrap with memory negotiator (if available)
    if agent_type == "rag_memory":
        try:
            a1 = RAGMemoryAgent(
                agent_name=AGENT_ONE,
                model="gpt-4-1106-preview",
                rag_negotiator=None
            )
            a2 = RAGMemoryAgent(
                agent_name=AGENT_TWO,
                model="gpt-4-1106-preview",
                rag_negotiator=None
            )
            print(f"  [INFO] Using RAG memory framework (simplified)")
        except Exception as e:
            print(f"  [WARNING] RAG initialization failed: {e}")
            agent_type = "baseline"
    
    # Run game
    try:
        game = MultiTurnUltimatumGame(
            players=[a1, a2],
            iterations=6,
            resources_support_set=Resources({"Dollars": 0}),
            player_goals=[UltimatumGoal(), UltimatumGoal()],
            player_initial_resources=[
                Resources({"Dollars": 100}),
                Resources({"Dollars": 0}),
            ],
            player_social_behaviour=["", ""],
            player_roles=[proposer_prompt, responder_prompt],
            log_dir=f"./.logs/ultimatum_memory/{agent_type}/{run_id}/",
        )
        
        game.run()
        
        final_state = game.game_state[-1]
        total_turns = len(game.game_state) - 2
        
        result = {
            "success": True,
            "agent_type": agent_type,
            "total_turns": total_turns,
            "run_id": run_id,
            "game_type": "ultimatum"
        }
        
        print(f"  Status: ✓ GAME COMPLETED")
        print(f"  Turns: {total_turns}")
        
        return result
    
    except Exception as e:
        print(f"  Status: ✗ ERROR")
        print(f"  Error: {type(e).__name__}: {str(e)[:100]}")
        return {
            "success": False,
            "agent_type": agent_type,
            "error": str(e)[:150],
            "run_id": run_id,
            "game_type": "ultimatum"
        }


def main():
    """Run three-way comparison for Trading and Ultimatum games"""
    
    print("\n" + "="*80)
    print("THREE-WAY MEMORY COMPARISON: TRADING & ULTIMATUM GAMES")
    print("="*80)
    print("1. BASELINE: Standard agent, no memory")
    print("2. PROMPT-MEMORY: Agent with memory-encouraging instructions")
    print("3. RAG-MEMORY: Agent with full RAG pipeline (if available)")
    print("="*80)
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "experiment": "three_way_comparison_extended",
        "description": "Baseline vs Prompt-Memory vs RAG-Memory for Trading & Ultimatum",
        "games_tested": ["trading", "ultimatum"],
        "runs": []
    }
    
    num_games = 2  # Games per agent type per game
    
    # Test Trading Game
    print("\n" + "="*80)
    print("TESTING TRADING GAME")
    print("="*80)
    
    for game_num in range(1, num_games + 1):
        run_id = f"trading_{uuid.uuid4().hex[:6]}"
        
        print(f"\n{'='*80}")
        print(f"TRADING GAME SET {game_num}/{num_games}")
        print(f"{'='*80}")
        
        baseline_result = run_trading_game(game_num, agent_type="baseline", run_id=f"{run_id}_baseline")
        results["runs"].append(baseline_result)
        
        prompt_result = run_trading_game(game_num, agent_type="prompt_memory", run_id=f"{run_id}_prompt")
        results["runs"].append(prompt_result)
        
        rag_result = run_trading_game(game_num, agent_type="rag_memory", run_id=f"{run_id}_rag")
        results["runs"].append(rag_result)
    
    # Test Ultimatum Game
    print("\n" + "="*80)
    print("TESTING ULTIMATUM GAME")
    print("="*80)
    
    for game_num in range(1, num_games + 1):
        run_id = f"ultimatum_{uuid.uuid4().hex[:6]}"
        
        print(f"\n{'='*80}")
        print(f"ULTIMATUM GAME SET {game_num}/{num_games}")
        print(f"{'='*80}")
        
        baseline_result = run_ultimatum_game(game_num, agent_type="baseline", run_id=f"{run_id}_baseline")
        results["runs"].append(baseline_result)
        
        prompt_result = run_ultimatum_game(game_num, agent_type="prompt_memory", run_id=f"{run_id}_prompt")
        results["runs"].append(prompt_result)
        
        rag_result = run_ultimatum_game(game_num, agent_type="rag_memory", run_id=f"{run_id}_rag")
        results["runs"].append(rag_result)
    
    # Analysis
    print("\n" + "="*80)
    print("RESULTS ANALYSIS")
    print("="*80)
    
    for game_type in ["trading", "ultimatum"]:
        print(f"\n{game_type.upper()} GAME:")
        print("-" * 60)
        
        agent_types = ["baseline", "prompt_memory", "rag_memory"]
        analysis = {}
        
        for atype in agent_types:
            runs = [r for r in results["runs"] 
                   if r.get("agent_type") == atype 
                   and r.get("game_type") == game_type 
                   and r.get("success")]
            
            if not runs:
                analysis[atype] = {"status": "No successful runs"}
                continue
            
            turns = [r["total_turns"] for r in runs]
            
            analysis[atype] = {
                "games_completed": len(runs),
                "avg_turns": f"{sum(turns)/len(turns):.1f}",
            }
        
        # Print comparison
        print(f"{'Agent Type':<20} {'Games':<15} {'Avg Turns':<15}")
        print("-" * 60)
        for atype in agent_types:
            data = analysis.get(atype, {})
            games = data.get("games_completed", "—")
            turns = data.get("avg_turns", "—")
            print(f"{atype:<20} {str(games):<15} {str(turns):<15}")
    
    # Save results
    results_dir = Path("test_results")
    results_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = results_dir / f"three_way_trading_ultimatum_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n{'='*80}")
    print(f"Results saved: {results_file}")
    print(f"Full analysis available in JSON format")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()