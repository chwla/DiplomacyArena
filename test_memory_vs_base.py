#!/usr/bin/env python3
"""
Memory Agent vs Baseline Agent - Pure Strategic Competition
- Both agents maximize their own profit
- No mandatory agreements - agents can walk away
- No moral framing - pure game theory
"""
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
load_dotenv(".env")

from negotiationarena.agents.chatgpt import ChatGPTAgent
from negotiationarena.agents.memory_agent_openai import MemoryAugmentedAgentOpenAI
from negotiationarena.game_objects.resource import Resources
from negotiationarena.game_objects.goal import UltimatumGoal
from negotiationarena.constants import AGENT_ONE, AGENT_TWO

# Import game
try:
    from games.ultimatum.game import MultiTurnUltimatumGame
    print("[INIT] ✓ Imported MultiTurnUltimatumGame")
except ImportError:
    try:
        from games.ultimatum.game import UltimatumGame as MultiTurnUltimatumGame
        print("[INIT] ✓ Imported UltimatumGame")
    except ImportError:
        try:
            from games.ultimatum.game import Game as MultiTurnUltimatumGame
            print("[INIT] ✓ Imported Game")
        except ImportError:
            print("[ERROR] Could not import ultimatum game")
            sys.exit(1)


def extract_final_dollars(game):
    """Extract final dollars - properly identify no-deals"""
    try:
        print("  [EXTRACT] Scanning for deal...")
        
        # Method 1: Look for ACCEPT
        for i, state in enumerate(game.game_state):
            if isinstance(state, dict):
                answer = str(state.get('player_answer', ''))
                
                if 'ACCEPT' in answer.upper():
                    # Find accepted trade
                    if i > 0:
                        prev_state = game.game_state[i-1]
                        trade = str(prev_state.get('newly_proposed_trade', ''))
                    else:
                        trade = str(state.get('newly_proposed_trade', ''))
                    
                    print(f"  [EXTRACT] Found ACCEPT at state {i}")
                    
                    if 'Dollars' in trade:
                        import re
                        match = re.search(r'RED\s+Gives\s+Dollars?:\s*(\d+)', trade, re.IGNORECASE)
                        if match:
                            red_gives = int(match.group(1))
                            p1_dollars = 100 - red_gives
                            p2_dollars = red_gives
                            
                            print(f"  [EXTRACT] Deal: RED=${p1_dollars}, BLUE=${p2_dollars}")
                            return p1_dollars, p2_dollars, True
        
        # Method 2: Check END state
        for state in reversed(game.game_state):
            if isinstance(state, dict) and state.get('current_iteration') == 'END':
                if 'summary' in state and 'final_resources' in state['summary']:
                    final_resources = state['summary']['final_resources']
                    if len(final_resources) >= 2:
                        p1_dollars = final_resources[0].get('Dollars', 0)
                        p2_dollars = final_resources[1].get('Dollars', 0)
                        
                        # CRITICAL: Check if this is a real deal or a failed negotiation
                        if p1_dollars + p2_dollars == 100 and p2_dollars > 0:
                            print(f"  [EXTRACT] From END: RED=${p1_dollars}, BLUE=${p2_dollars}")
                            return p1_dollars, p2_dollars, True
                        elif p1_dollars == 100 and p2_dollars == 0:
                            print(f"  [EXTRACT] NO DEAL - BLUE got nothing (negotiation failed)")
                            return 0, 0, True
        
        # No deal found
        print("  [EXTRACT] NO DEAL - Both walked away")
        return 0, 0, True
        
    except Exception as e:
        print(f"  [ERROR] Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return 0, 0, False


def run_one_game(game_num, memory_agent, baseline_agent, debug=False):
    """Run single game with complete freedom"""
    
    print(f"\n{'='*60}")
    print(f"GAME {game_num}")
    
    # Show memory
    mem = memory_agent.opponent_history
    if mem['games_played'] > 0:
        print(f"Memory Agent intel: opponent accepts ≥{mem['min_accepted_pct']:.0f}%")
    else:
        print(f"Memory Agent: exploring (no intel)")
    print(f"{'='*60}")
    
    # Pure strategic prompts - no moral language
    proposer_prompt = (
        f"You are {AGENT_ONE}. You control 100 Dollars. "
        f"Propose how to split with {AGENT_TWO}. "
        f"Your objective: maximize YOUR dollars. "
        f"You propose on exchanges 1, 3, 5. "
        f"{AGENT_TWO} responds on exchanges 2, 4, 6. "
        f"If no agreement by exchange 6, both get $0."
    )
    
    responder_prompt = (
        f"You are {AGENT_TWO}. {AGENT_ONE} proposes splits. "
        f"Your objective: maximize YOUR dollars. "
        f"You respond on exchanges 2, 4, 6. "
        f"You can accept or counter-propose. "
        f"If no agreement by exchange 6, both get $0."
    )
    
    try:
        game = MultiTurnUltimatumGame(
            players=[memory_agent, baseline_agent],
            iterations=6,
            resources_support_set=Resources({"Dollars": 0}),
            player_goals=[UltimatumGoal(), UltimatumGoal()],
            player_initial_resources=[
                Resources({"Dollars": 100}),
                Resources({"Dollars": 0}),
            ],
            player_social_behaviour=["", ""],
            player_roles=[proposer_prompt, responder_prompt],
            log_dir=f"./.logs/strategic_test/game_{game_num}/",
        )
        
        print("  Starting negotiation...")
        game.run()
        print("  ✓ Negotiation completed")
        
        # Debug first game
        if debug and hasattr(game, 'game_state'):
            print(f"\n  [DEBUG] Last 5 states:")
            for i, state in enumerate(game.game_state[-5:]):
                if isinstance(state, dict):
                    iteration = state.get('current_iteration', 'N/A')
                    answer = state.get('player_answer', 'N/A')
                    trade = state.get('newly_proposed_trade', 'N/A')
                    print(f"    State {i}: iter={iteration}")
                    print(f"      answer={str(answer)[:50]}")
                    print(f"      trade={str(trade)[:60]}")
        
        # Extract results
        print("  Extracting final state...")
        p1_dollars, p2_dollars, success = extract_final_dollars(game)
        
        if not success:
            print("  [WARNING] Extraction uncertain")
            log_dir = Path(f"./.logs/strategic_test/game_{game_num}")
            if log_dir.exists():
                print(f"  [INFO] Check logs: {log_dir}")
        
        deal_made = (p1_dollars + p2_dollars) > 0
        
        # Update memory
        if success:
            memory_agent.update_game_result(deal_made, p1_dollars, p2_dollars)
        
        # Print result
        print(f"\n  Result: Memory=${p1_dollars}, Baseline=${p2_dollars}")
        if deal_made:
            print(f"  ✓ DEAL REACHED - Memory: {p1_dollars}%, Baseline: {p2_dollars}%")
        else:
            print(f"  → NO DEAL - Both walked away")
        
        return {
            "game": game_num,
            "memory_dollars": p1_dollars,
            "baseline_dollars": p2_dollars,
            "deal_made": deal_made,
            "success": success
        }
        
    except Exception as e:
        print(f"\n  ✗ GAME CRASHED: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "game": game_num,
            "memory_dollars": 0,
            "baseline_dollars": 0,
            "deal_made": False,
            "success": False,
            "error": str(e)
        }


def main():
    print("\n" + "="*60)
    print("MEMORY vs BASELINE - STRATEGIC COMPETITION")
    print("="*60)
    print("Model: GPT-3.5-TURBO")
    print("Proposer: MEMORY AGENT (learns opponent behavior)")
    print("Responder: BASELINE AGENT (no memory)")
    print("Goal: Both maximize profit")
    print("Freedom: Agents can walk away (no mandatory deals)")
    print("Exchanges: 6 total (RED->BLUE->RED->BLUE->RED->BLUE)")
    print("="*60)
    
    # Create agents
    print("\nInitializing agents...")
    
    memory_agent = MemoryAugmentedAgentOpenAI(
        agent_name=AGENT_ONE,
        model="gpt-3.5-turbo",
        temperature=0.3,
        memory_config={"enabled": True}
    )
    print("✓ Memory agent ready")
    
    baseline_agent = ChatGPTAgent(
        agent_name=AGENT_TWO,
        model="gpt-3.5-turbo",
        temperature=0.4
    )
    print("✓ Baseline agent ready")
    
    # Run games
    num_games = 20
    results = []
    
    for game_num in range(1, num_games + 1):
        result = run_one_game(game_num, memory_agent, baseline_agent, debug=(game_num == 1))
        results.append(result)
        
        # Stop on crashes
        failures = sum(1 for r in results if not r.get('success', False))
        if failures >= 3:
            print(f"\n⚠️ Stopping: {failures} extraction failures")
            break
    
    # Analysis
    print("\n" + "="*60)
    print("FINAL RESULTS")
    print("="*60)
    
    successful = [r for r in results if r.get('success', False)]
    deals = [r for r in successful if r.get('deal_made', False)]
    no_deals = [r for r in successful if not r.get('deal_made', False)]
    
    print(f"\nTotal games: {len(successful)}")
    print(f"Deals reached: {len(deals)}")
    print(f"Walk-aways: {len(no_deals)}")
    
    if not deals:
        print("\n✗ No deals made - agents walked away every time")
        return
    
    print(f"\n--- Deal Analysis ({len(deals)} games) ---")
    
    # Performance over time
    if len(deals) >= 4:
        mid = len(deals) // 2
        first_half = deals[:mid]
        second_half = deals[mid:]
        
        avg_first = sum(r['memory_dollars'] for r in first_half) / len(first_half)
        avg_second = sum(r['memory_dollars'] for r in second_half) / len(second_half)
        
        print(f"\nMemory Agent Performance:")
        print(f"  Early games ({len(first_half)}):  ${avg_first:.1f} avg")
        print(f"  Later games ({len(second_half)}): ${avg_second:.1f} avg")
        print(f"  Improvement:          ${avg_second - avg_first:+.1f}")
        
        if avg_second > avg_first + 3:
            print(f"  ✓ LEARNING DETECTED: Agent improved through experience")
        elif avg_second > avg_first:
            print(f"  ≈ Slight improvement")
        else:
            print(f"  → No clear improvement (needs more games)")
    
    print(f"\nOverall Averages (deals only):")
    avg_memory = sum(r['memory_dollars'] for r in deals) / len(deals)
    avg_baseline = sum(r['baseline_dollars'] for r in deals) / len(deals)
    print(f"  Memory agent:  ${avg_memory:.1f}")
    print(f"  Baseline:      ${avg_baseline:.1f}")
    print(f"  Difference:    ${avg_memory - avg_baseline:+.1f}")
    
    # Show learned intel
    mem = memory_agent.opponent_history
    if mem['games_played'] > 0:
        print(f"\nLearned Intelligence:")
        print(f"  Total games:           {mem['games_played']}")
        print(f"  Opponent accepts ≥:    {mem['min_accepted_pct']:.0f}%")
        if mem['max_rejected_pct'] > 0:
            print(f"  Opponent rejected:     {mem['max_rejected_pct']:.0f}%")
        
        # Show pattern
        if mem['acceptance_history']:
            print(f"\n  Acceptance pattern (last 5):")
            for offer, accepted in mem['acceptance_history'][-5:]:
                status = "✓" if accepted else "✗"
                print(f"    {status} {offer:.0f}%")
    
    # Game-by-game breakdown
    print(f"\nGame-by-Game Results:")
    for r in successful:
        if r['deal_made']:
            print(f"  Game {r['game']}: Memory=${r['memory_dollars']}, Baseline=${r['baseline_dollars']}")
        else:
            print(f"  Game {r['game']}: NO DEAL (both walked)")
    
    # Final verdict
    print("\n" + "="*60)
    if len(deals) >= 5:
        mid = len(deals) // 2
        first_half = deals[:mid]
        second_half = deals[mid:]
        avg_first = sum(r['memory_dollars'] for r in first_half) / len(first_half)
        avg_second = sum(r['memory_dollars'] for r in second_half) / len(second_half)
        
        if avg_second > avg_first + 3:
            print("✓ MEMORY ADVANTAGE: Agent learned and exploited patterns")
        elif avg_second > avg_first:
            print("≈ Memory enabled, slight advantage detected")
        else:
            print("≈ Memory enabled but needs more games for clear advantage")
    else:
        print("≈ INCOMPLETE: Need more games to evaluate")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()