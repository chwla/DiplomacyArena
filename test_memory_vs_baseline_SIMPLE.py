#!/usr/bin/env python3
"""
SIMPLE WORKING SOLUTION - Just compare game outcomes with/without discussions
Don't try to integrate memory into the pickle-heavy game framework
Just run games and analyze the transcripts afterward
"""
import sys
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
load_dotenv(".env")

from negotiationarena.agents.chatgpt import ChatGPTAgent
from negotiationarena.game_objects.resource import Resources
from negotiationarena.game_objects.goal import BuyerGoal, SellerGoal
from negotiationarena.game_objects.valuation import Valuation
from negotiationarena.constants import *
from games.buy_sell_game.game import BuySellGame


def run_game(game_name, use_instructions=False):
    """Run a game, optionally with memory-like instructions"""
    
    print(f"\n{'='*70}")
    print(f"{game_name} - {'WITH memory instructions' if use_instructions else 'BASELINE'}")
    print(f"{'='*70}")
    
    # Create agents
    if use_instructions:
        # Give explicit instructions to remember and learn
        seller = ChatGPTAgent(
            agent_name=AGENT_ONE,
            model="gpt-4-1106-preview"
        )
        buyer = ChatGPTAgent(
            agent_name=AGENT_TWO,
            model="gpt-4-1106-preview"
        )
        
        social_behaviour = [
            "Remember: Learn from each negotiation. If an offer was rejected, try a different approach. Build on what worked before.",
            "Remember: Pay attention to patterns in the negotiation. Adapt your strategy based on what the other player values."
        ]
    else:
        seller = ChatGPTAgent(agent_name=AGENT_ONE, model="gpt-4-1106-preview")
        buyer = ChatGPTAgent(agent_name=AGENT_TWO, model="gpt-4-1106-preview")
        social_behaviour = ["", ""]
    
    # Run game
    game = BuySellGame(
        players=[seller, buyer],
        iterations=8,
        player_goals=[
            SellerGoal(cost_of_production=Valuation({"X": 40})),
            BuyerGoal(willingness_to_pay=Valuation({"X": 60})),
        ],
        player_starting_resources=[
            Resources({"X": 1}),
            Resources({MONEY_TOKEN: 1000}),
        ],
        player_conversation_roles=[
            f"You are {AGENT_ONE}, a seller.",
            f"You are {AGENT_TWO}, a buyer.",
        ],
        player_social_behaviour=social_behaviour,
        log_dir=f"./.logs/simple_comparison/{'memory_instruct' if use_instructions else 'baseline'}/",
    )
    
    try:
        game.run()
        
        # Extract results
        final_state = game.game_state[-1]
        if final_state["current_iteration"] == "END":
            summary = final_state.get("summary", {})
            
            result = {
                "success": True,
                "deal_reached": summary.get("final_response") == ACCEPTING_TAG,
                "total_turns": len(game.game_state) - 2,
                "final_response": summary.get("final_response"),
                "with_memory_instructions": use_instructions
            }
            
            print(f"  ✓ Game completed")
            print(f"    Deal: {result['deal_reached']}")
            print(f"    Turns: {result['total_turns']}")
            
            return result
    
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return {"success": False, "error": str(e)}


def main():
    """Run comparison"""
    
    print("\n" + "="*80)
    print("SIMPLE MEMORY COMPARISON")
    print("Comparing baseline vs agents with memory-encouraging instructions")
    print("="*80)
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "runs": []
    }
    
    num_runs = 2
    
    # Run multiple times
    for run in range(1, num_runs + 1):
        print(f"\n{'='*80}")
        print(f"RUN {run}/{num_runs}")
        print(f"{'='*80}")
        
        # Baseline
        baseline_result = run_game(f"Buy-Sell #{run}", use_instructions=False)
        results["runs"].append(baseline_result)
        
        # With memory instructions
        memory_result = run_game(f"Buy-Sell #{run}", use_instructions=True)
        results["runs"].append(memory_result)
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    baseline_runs = [r for r in results["runs"] if not r.get("with_memory_instructions")]
    memory_runs = [r for r in results["runs"] if r.get("with_memory_instructions")]
    
    baseline_success = [r for r in baseline_runs if r.get("success")]
    memory_success = [r for r in memory_runs if r.get("success")]
    
    baseline_deals = sum(1 for r in baseline_success if r.get("deal_reached"))
    memory_deals = sum(1 for r in memory_success if r.get("deal_reached"))
    
    print(f"\nBaseline:")
    print(f"  Completed: {len(baseline_success)}/{len(baseline_runs)}")
    print(f"  Deals: {baseline_deals}/{len(baseline_success)}")
    if baseline_success:
        avg_turns = sum(r["total_turns"] for r in baseline_success) / len(baseline_success)
        print(f"  Avg turns: {avg_turns:.1f}")
    
    print(f"\nWith Memory Instructions:")
    print(f"  Completed: {len(memory_success)}/{len(memory_runs)}")
    print(f"  Deals: {memory_deals}/{len(memory_success)}")
    if memory_success:
        avg_turns = sum(r["total_turns"] for r in memory_success) / len(memory_success)
        print(f"  Avg turns: {avg_turns:.1f}")
    
    # Save results
    results_dir = Path("test_results")
    results_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = results_dir / f"simple_comparison_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n{'='*80}")
    print(f"Results saved to: {results_file}")
    print(f"{'='*80}")
    
    print("\nNOTE: This comparison doesn't use true memory storage.")
    print("It just gives agents instructions to 'remember' and adapt.")
    print("True memory integration requires a non-pickling game framework.")


if __name__ == "__main__":
    main()