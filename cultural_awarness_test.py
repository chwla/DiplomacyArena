#!/usr/bin/env python3
"""
Comprehensive test runner for all negotiation games with cultural awareness
"""

import sys
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))

from negotiationarena.agents.chatgpt import ChatGPTAgent
from negotiationarena.game_objects.resource import Resources
from negotiationarena.game_objects.goal import ResourceGoal, UltimatumGoal, BuyerGoal, SellerGoal
from negotiationarena.game_objects.valuation import Valuation
from negotiationarena.constants import *
from negotiationarena.cultural_profile import CulturalProfileManager
from negotiationarena.cultural_prompts import CulturalPromptBuilder

# Import games
try:
    from games.simple_game.game import SimpleGame
    SIMPLE_GAME_AVAILABLE = True
except ImportError as e:
    print(f"⚠ Warning: Could not import SimpleGame: {e}")
    SIMPLE_GAME_AVAILABLE = False

try:
    from games.trading_game.game import TradingGame
    TRADING_GAME_AVAILABLE = True
except ImportError as e:
    print(f"⚠ Warning: Could not import TradingGame: {e}")
    TRADING_GAME_AVAILABLE = False

try:
    from games.ultimatum.game import MultiTurnUltimatumGame
    ULTIMATUM_GAME_AVAILABLE = True
except ImportError as e:
    print(f"⚠ Warning: Could not import UltimatumGame: {e}")
    ULTIMATUM_GAME_AVAILABLE = False

try:
    from games.buy_sell_game.game import BuySellGame
    BUYSELL_GAME_AVAILABLE = True
except ImportError as e:
    print(f"⚠ Warning: Could not import BuySellGame: {e}")
    BUYSELL_GAME_AVAILABLE = False

load_dotenv(".env")


def test_simple_game(country1="u.s.a.", country2="china", with_culture=True):
    """Test Simple Game with cultural awareness"""
    if not SIMPLE_GAME_AVAILABLE:
        return None, "SimpleGame not available"
    
    try:
        prompt_builder = CulturalPromptBuilder()
        manager = CulturalProfileManager()
        
        a1 = ChatGPTAgent(model="gpt-4-1106-preview", agent_name=AGENT_ONE)
        a2 = ChatGPTAgent(model="gpt-4-1106-preview", agent_name=AGENT_TWO)
        
        if with_culture:
            p1 = manager.get_profile(country1)
            p2 = manager.get_profile(country2)
            c1 = prompt_builder.build_system_prompt(country=country1, base_role="trader")
            c2 = prompt_builder.build_system_prompt(country=country2, base_role="trader")
            social_behaviour = [
                p1.interaction_profile.behaviour_rules if p1 else "",
                p2.interaction_profile.behaviour_rules if p2 else "",
            ]
        else:
            social_behaviour = ["", ""]
        
        game = SimpleGame(
            players=[a1, a2],
            iterations=6,
            resources_support_set=Resources({"X": 0, "Y": 0}),
            player_initial_resources=[
                Resources({"X": 25, "Y": 5}),
                Resources({"X": 0, "Y": 0}),
            ],
            player_social_behaviour=social_behaviour,
            player_roles=[
                f"You are {AGENT_ONE}, start by making a proposal.",
                f"You are {AGENT_TWO}, start by accepting a trade.",
            ],
            log_dir="./.logs/simple_game/",
        )
        
        result = game.run()
        return result, None
    except Exception as e:
        return None, str(e)


def test_trading_game(country1="u.s.a.", country2="china", with_culture=True):
    """Test Trading Game with cultural awareness"""
    if not TRADING_GAME_AVAILABLE:
        return None, "TradingGame not available"
    
    try:
        prompt_builder = CulturalPromptBuilder()
        manager = CulturalProfileManager()
        
        a1 = ChatGPTAgent(model="gpt-4-1106-preview", agent_name=AGENT_ONE)
        a2 = ChatGPTAgent(model="gpt-4-1106-preview", agent_name=AGENT_TWO)
        
        if with_culture:
            p1 = manager.get_profile(country1)
            p2 = manager.get_profile(country2)
            social_behaviour = [
                p1.interaction_profile.behaviour_rules if p1 else "",
                p2.interaction_profile.behaviour_rules if p2 else "",
            ]
        else:
            social_behaviour = ["", ""]
        
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
            player_social_behaviour=social_behaviour,
            player_roles=[
                f"You are {AGENT_ONE}, start by making a proposal.",
                f"You are {AGENT_TWO}, start by responding to a trade.",
            ],
            log_dir="./.logs/trading/",
        )
        
        result = game.run()
        return result, None
    except Exception as e:
        return None, str(e)


def test_ultimatum_game(country1="u.s.a.", country2="china", with_culture=True):
    """Test Ultimatum Game with cultural awareness"""
    if not ULTIMATUM_GAME_AVAILABLE:
        return None, "UltimatumGame not available"
    
    try:
        prompt_builder = CulturalPromptBuilder()
        manager = CulturalProfileManager()
        
        a1 = ChatGPTAgent(agent_name=AGENT_ONE, model="gpt-4-1106-preview")
        a2 = ChatGPTAgent(agent_name=AGENT_TWO, model="gpt-4-1106-preview")
        
        if with_culture:
            p1 = manager.get_profile(country1)
            p2 = manager.get_profile(country2)
            social_behaviour = [
                p1.interaction_profile.behaviour_rules if p1 else "",
                p2.interaction_profile.behaviour_rules if p2 else "",
            ]
        else:
            social_behaviour = ["", ""]
        
        game = MultiTurnUltimatumGame(
            players=[a1, a2],
            iterations=6,
            resources_support_set=Resources({"Dollars": 0}),
            player_goals=[UltimatumGoal(), UltimatumGoal()],
            player_initial_resources=[
                Resources({"Dollars": 100}),
                Resources({"Dollars": 0}),
            ],
            player_social_behaviour=social_behaviour,
            player_roles=[
                f"You are {AGENT_ONE}.",
                f"You are {AGENT_TWO}.",
            ],
            log_dir="./.logs/ultimatum/",
        )
        
        result = game.run()
        return result, None
    except Exception as e:
        return None, str(e)


def test_buysell_game(country1="u.s.a.", country2="china", with_culture=True):
    """Test Buy-Sell Game with cultural awareness"""
    if not BUYSELL_GAME_AVAILABLE:
        return None, "BuySellGame not available"
    
    try:
        prompt_builder = CulturalPromptBuilder()
        manager = CulturalProfileManager()
        
        a1 = ChatGPTAgent(agent_name=AGENT_ONE, model="gpt-4-1106-preview")
        a2 = ChatGPTAgent(agent_name=AGENT_TWO, model="gpt-4-1106-preview")
        
        if with_culture:
            p1 = manager.get_profile(country1)
            p2 = manager.get_profile(country2)
            c1 = prompt_builder.build_system_prompt(country=country1, base_role="seller")
            c2 = prompt_builder.build_system_prompt(country=country2, base_role="buyer")
            roles = [
                f"You are {AGENT_ONE}, a seller from {country1}. {c1}",
                f"You are {AGENT_TWO}, a buyer from {country2}. {c2}",
            ]
            social_behaviour = [
                p1.interaction_profile.behaviour_rules if p1 else "",
                p2.interaction_profile.behaviour_rules if p2 else "",
            ]
        else:
            roles = [f"You are {AGENT_ONE}.", f"You are {AGENT_TWO}."]
            social_behaviour = ["", ""]
        
        game = BuySellGame(
            players=[a1, a2],
            iterations=10,
            player_goals=[
                SellerGoal(cost_of_production=Valuation({"X": 40})),
                BuyerGoal(willingness_to_pay=Valuation({"X": 60})),
            ],
            player_starting_resources=[
                Resources({"X": 1}),
                Resources({MONEY_TOKEN: 1000}),
            ],
            player_conversation_roles=roles,
            player_social_behaviour=social_behaviour,
            log_dir="./.logs/buysell/",
        )
        
        result = game.run()
        return result, None
    except Exception as e:
        return None, str(e)


def run_all_tests():
    """Run all game tests"""
    print("\n" + "="*80)
    print("RUNNING ALL GAME TESTS")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "games": {}
    }
    
    games = [
        ("Simple Game", test_simple_game, SIMPLE_GAME_AVAILABLE),
        ("Trading Game", test_trading_game, TRADING_GAME_AVAILABLE),
        ("Ultimatum Game", test_ultimatum_game, ULTIMATUM_GAME_AVAILABLE),
        ("Buy-Sell Game", test_buysell_game, BUYSELL_GAME_AVAILABLE),
    ]
    
    for game_name, test_func, available in games:
        print(f"\n{'='*80}")
        print(f"Testing: {game_name}")
        print(f"{'='*80}")
        
        if not available:
            print(f"  ⊘ {game_name} not available - skipping")
            results["games"][game_name] = {"status": "unavailable"}
            continue
        
        game_results = {"cultural": [], "baseline": []}
        
        # Test with cultural awareness
        print(f"\n  Running WITH cultural awareness...")
        result, error = test_func(with_culture=True)
        if error:
            print(f"    ✗ Error: {error}")
            game_results["cultural"].append({"status": "failed", "error": error})
        else:
            print(f"    ✓ Success")
            game_results["cultural"].append({"status": "success"})
        
        # Test baseline (no cultural awareness)
        print(f"\n  Running BASELINE (no cultural awareness)...")
        result, error = test_func(with_culture=False)
        if error:
            print(f"    ✗ Error: {error}")
            game_results["baseline"].append({"status": "failed", "error": error})
        else:
            print(f"    ✓ Success")
            game_results["baseline"].append({"status": "success"})
        
        results["games"][game_name] = game_results
    
    # Save results
    results_dir = Path("test_results")
    results_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = results_dir / f"all_games_test_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    
    for game_name, game_result in results["games"].items():
        if game_result.get("status") == "unavailable":
            print(f"\n{game_name}: UNAVAILABLE")
        else:
            cultural_success = sum(1 for r in game_result["cultural"] if r["status"] == "success")
            baseline_success = sum(1 for r in game_result["baseline"] if r["status"] == "success")
            print(f"\n{game_name}:")
            print(f"  Cultural: {cultural_success}/{len(game_result['cultural'])} successful")
            print(f"  Baseline: {baseline_success}/{len(game_result['baseline'])} successful")
    
    print(f"\n{'='*80}")
    print(f"Results saved to: {results_file}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    run_all_tests()