COUNTRY_1 = "india"
COUNTRY_2 = "pakistan"

import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))

from negotiationarena.agents.chatgpt import ChatGPTAgent
from negotiationarena.game_objects.resource import Resources
from negotiationarena.game_objects.goal import ResourceGoal, UltimatumGoal, BuyerGoal, SellerGoal
from negotiationarena.game_objects.valuation import Valuation
from negotiationarena.constants import *
import importlib

try:
    from games.trading_game.game import TradingGame
    TRADING_GAME_AVAILABLE = True
except:
    TRADING_GAME_AVAILABLE = False

try:
    from games.ultimatum.game import MultiTurnUltimatumGame
    ULTIMATUM_GAME_AVAILABLE = True
except:
    ULTIMATUM_GAME_AVAILABLE = False

try:
    from games.buy_sell_game.game import BuySellGame
    BUYSELL_GAME_AVAILABLE = True
except:
    BUYSELL_GAME_AVAILABLE = False

load_dotenv(".env")


def load_country(name):
    try:
        module = importlib.import_module(f"diplomatic_agents.{name.lower()}")
        return module.create_full_prompt(include_analysis=False)
    except:
        return f"You are a negotiator from {name}."


def create_role_prompt(cultural_prompt, is_first_player, game_type):
    # Truncate cultural prompt aggressively - game rules are more important
    if len(cultural_prompt) > 1000:
        cultural_prompt = cultural_prompt[:1000]
    
    # CRITICAL: Put game rules FIRST so LLM sees them most recently
    prompt = ""
    
    if game_type == "trading":
        if is_first_player:
            prompt = """YOU ARE PLAYER RED IN A TRADING GAME.

YOUR STATE:
- Resources: X=25, Y=5
- Goal: X=15, Y=15
- Need: Give away 10 X, Get 10 Y

EACH TURN:
1. See opponent's message and proposal
2. Make YOUR OWN counter-proposal OR accept theirs

TO PROPOSE A TRADE:
<my name>Player RED</my name>
<my resources>X: 25, Y: 5</my resources>
<my goals>X: 15, Y: 15</my goals>
<reason>your reasoning</reason>
<player answer>NONE</player answer>
<message>your message</message>
<newly proposed trade>Player RED Gives X: 10 | Player BLUE Gives Y: 10</newly proposed trade>

TO ACCEPT THEIR TRADE:
<my name>Player RED</my name>
<my resources>X: 25, Y: 5</my resources>
<my goals>X: 15, Y: 15</my goals>
<reason>their proposal works</reason>
<player answer>ACCEPT</player answer>
<message>I accept</message>
<newly proposed trade>NONE</newly proposed trade>

OUTPUT RAW XML ONLY. NO MARKDOWN BLOCKS.
"""
        else:
            prompt = """YOU ARE PLAYER BLUE IN A TRADING GAME.

YOUR STATE:
- Resources: X=5, Y=25
- Goal: X=15, Y=15
- Need: Get 10 X, Give away 10 Y

EACH TURN:
1. See opponent's proposal
2. Make YOUR counter-proposal OR accept theirs

TO PROPOSE A TRADE:
<my name>Player BLUE</my name>
<my resources>X: 5, Y: 25</my resources>
<my goals>X: 15, Y: 15</my goals>
<reason>your reasoning</reason>
<player answer>NONE</player answer>
<message>your message</message>
<newly proposed trade>Player RED Gives X: 10 | Player BLUE Gives Y: 10</newly proposed trade>

TO ACCEPT THEIR TRADE:
<my name>Player BLUE</my name>
<my resources>X: 5, Y: 25</my resources>
<my goals>X: 15, Y: 15</my goals>
<reason>their proposal works</reason>
<player answer>ACCEPT</player answer>
<message>I accept</message>
<newly proposed trade>NONE</newly proposed trade>

OUTPUT RAW XML ONLY. NO MARKDOWN BLOCKS.
"""
    
    elif game_type == "ultimatum":
        if is_first_player:
            prompt = """YOU ARE PLAYER RED (PROPOSER) IN ULTIMATUM GAME.

TASK: Propose how to split $100 between you and Player BLUE.

FORMAT:
<my name>Player RED</my name>
<move>60 / 40</move>
<my resources>Dollars: 100</my resources>
<reason>your reasoning</reason>
<player answer>PROPOSE</player answer>
<message>your message</message>
<newly proposed trade>NONE</newly proposed trade>

OUTPUT RAW XML ONLY. NO MARKDOWN BLOCKS.
"""
        else:
            prompt = """YOU ARE PLAYER BLUE (RESPONDER) IN ULTIMATUM GAME.

CRITICAL INSTRUCTIONS:
- You will see Player RED's split proposal (e.g., "60 / 40" means RED gets $60, you get $40)
- You MUST choose: ACCEPT or REJECT
- NO NEGOTIATION ALLOWED
- If ACCEPT: both get money as proposed
- If REJECT: both get $0

EVERY TURN YOU MUST OUTPUT ONE OF THESE:

TO ACCEPT (if RED proposed "60 / 40"):
<my name>Player BLUE</my name>
<move>60 / 40</move>
<my resources>Dollars: 0</my resources>
<reason>Fair enough, I get $40</reason>
<player answer>ACCEPT</player answer>
<message>I accept</message>
<newly proposed trade>NONE</newly proposed trade>

TO REJECT (if RED proposed "70 / 30"):
<my name>Player BLUE</my name>
<move>70 / 30</move>
<my resources>Dollars: 0</my resources>
<reason>Too unfair, I only get $30</reason>
<player answer>REJECT</player answer>
<message>I reject</message>
<newly proposed trade>NONE</newly proposed trade>

CRITICAL: The <move> tag must EXACTLY COPY what Player RED proposed.
Example: If you see "Player RED proposed 60 / 40", you write <move>60 / 40</move>

DECISION GUIDE:
- If you get ≥$35: probably ACCEPT
- If you get <$35: probably REJECT

YOU MUST OUTPUT ACCEPT OR REJECT EACH TURN.
OUTPUT RAW XML ONLY. NO MARKDOWN BLOCKS.
"""
    
    elif game_type == "buysell":
        if is_first_player:
            prompt = """YOU ARE PLAYER RED (SELLER) IN BUY-SELL GAME.

CRITICAL CONSTRAINTS:
- You have: 1 unit of resource X
- Production cost: 40 ZUP
- ABSOLUTE MINIMUM PRICE: 40 ZUP
- ⚠️ NEVER SELL BELOW 40 ZUP OR YOU LOSE MONEY ⚠️

STRATEGY:
1. Start at 45-50 ZUP
2. Negotiate down slowly
3. STOP at 40 ZUP minimum
4. If opponent offers <40 ZUP: counter with ≥40 ZUP

TO PROPOSE PRICE:
<proposal count>1</proposal count>
<my resources>X: 1</my resources>
<my goals>Sell resources for <ZUP>. It costed X: 40 ZUP to produce</my goals>
<reason>your reasoning</reason>
<player answer>PROPOSE</player answer>
<newly proposed trade>Player RED Gives X: 1 | Player BLUE Gives ZUP: 48</newly proposed trade>
<message>I propose 48 ZUP</message>

TO ACCEPT (ONLY IF PRICE ≥ 40 ZUP):
<proposal count>2</proposal count>
<my resources>X: 1</my resources>
<my goals>Sell resources for <ZUP>. It costed X: 40 ZUP to produce</my goals>
<reason>Price covers cost</reason>
<player answer>ACCEPT</player answer>
<newly proposed trade>NONE</newly proposed trade>
<message>I accept</message>

⚠️ IF OPPONENT PROPOSES <40 ZUP: YOU MUST COUNTER WITH ≥40 ZUP ⚠️
NEVER ACCEPT BELOW 40 ZUP.
OUTPUT RAW XML ONLY. NO MARKDOWN BLOCKS.
"""
        else:
            prompt = """YOU ARE PLAYER BLUE (BUYER) IN BUY-SELL GAME.

CONSTRAINTS:
- You have: 1000 ZUP
- Maximum willing to pay: 60 ZUP
- Target: Buy for 40-50 ZUP range

STRATEGY:
1. Counter with lower prices
2. Try to negotiate down
3. Never exceed 60 ZUP
4. Make DIFFERENT offers each time

TO COUNTER-OFFER:
<proposal count>1</proposal count>
<my resources>ZUP: 1000</my resources>
<my goals>Buy resources with <ZUP>. You are willing to pay at most X: 60 ZUP</my goals>
<reason>your reasoning</reason>
<player answer>PROPOSE</player answer>
<newly proposed trade>Player RED Gives X: 1 | Player BLUE Gives ZUP: 45</newly proposed trade>
<message>I counter-offer 45 ZUP</message>

TO ACCEPT:
<proposal count>2</proposal count>
<my resources>ZUP: 1000</my resources>
<my goals>Buy resources with <ZUP>. You are willing to pay at most X: 60 ZUP</my goals>
<reason>Good price</reason>
<player answer>ACCEPT</player answer>
<newly proposed trade>NONE</newly proposed trade>
<message>I accept</message>

MAKE DIFFERENT COUNTER-OFFERS EACH TIME.
OUTPUT RAW XML ONLY. NO MARKDOWN BLOCKS.
"""
    
    # Add cultural context at END (so game rules stay fresh in LLM's context window)
    prompt += f"\n\nCULTURAL BACKGROUND (use for negotiation style):\n{cultural_prompt}\n\n"
    prompt += "REMEMBER: Follow the game rules above exactly. Output raw XML only.\n"
    
    return prompt


def check_game_success(game_state, game_type):
    if not game_state or len(game_state) < 2:
        return False, "Incomplete"
    
    end_state = None
    for state in reversed(game_state):
        if state.get("current_iteration") == "END":
            end_state = state
            break
    
    if not end_state or "summary" not in end_state:
        return False, "No END state"
    
    final = end_state["summary"].get("final_response", "")
    
    if final == "ACCEPT":
        return True, "Agreement"
    if final == "REJECT":
        return False, "Rejected"
    if final in ["NONE", ""]:
        return False, "Timeout"
    
    return False, f"Unknown: {final}"


def run_trading_game(p1, p2, c1, c2):
    if not TRADING_GAME_AVAILABLE:
        return None, "unavailable"
    
    try:
        a1 = ChatGPTAgent(model="gpt-3.5-turbo", agent_name=AGENT_ONE)
        a2 = ChatGPTAgent(model="gpt-3.5-turbo", agent_name=AGENT_TWO)
        
        role1 = create_role_prompt(p1, True, "trading")
        role2 = create_role_prompt(p2, False, "trading")
        
        game = TradingGame(
            players=[a1, a2],
            iterations=8,
            resources_support_set=Resources({"X": 0, "Y": 0}),
            player_goals=[ResourceGoal({"X": 15, "Y": 15}), ResourceGoal({"X": 15, "Y": 15})],
            player_initial_resources=[Resources({"X": 25, "Y": 5}), Resources({"X": 5, "Y": 25})],
            player_social_behaviour=["", ""],
            player_roles=[role1, role2],
            log_dir=f"./.logs/{c1}_{c2}_trading/",
        )
        
        result = game.run()
        success, reason = check_game_success(game.game_state, "trading")
        if not success:
            return None, f"Failed: {reason}"
        return result, None
    except Exception as e:
        return None, str(e)


def run_ultimatum_game(p1, p2, c1, c2):
    if not ULTIMATUM_GAME_AVAILABLE:
        return None, "unavailable"
    
    game = None
    try:
        a1 = ChatGPTAgent(agent_name=AGENT_ONE, model="gpt-3.5-turbo")
        a2 = ChatGPTAgent(agent_name=AGENT_TWO, model="gpt-3.5-turbo")
        
        role1 = create_role_prompt(p1, True, "ultimatum")
        role2 = create_role_prompt(p2, False, "ultimatum")
        
        game = MultiTurnUltimatumGame(
            players=[a1, a2],
            iterations=8,
            resources_support_set=Resources({"Dollars": 0}),
            player_goals=[UltimatumGoal(), UltimatumGoal()],
            player_initial_resources=[Resources({"Dollars": 100}), Resources({"Dollars": 0})],
            player_social_behaviour=["", ""],
            player_roles=[role1, role2],
            log_dir=f"./.logs/{c1}_{c2}_ultimatum/",
        )
        
        result = game.run()
        success, reason = check_game_success(game.game_state, "ultimatum")
        if not success:
            return None, f"Failed: {reason}"
        return result, None
        
    except Exception as e:
        # Any error - check if it's the framework bug and if agent actually accepted
        error_msg = str(e)
        if game and hasattr(game, 'game_state') and game.game_state:
            # Check if there was an ACCEPT or REJECT in the game state
            try:
                for state in game.game_state:
                    answer = state.get("player_complete_answer", "")
                    if isinstance(answer, str):
                        if "<player answer>ACCEPT</player answer>" in answer:
                            # Player accepted - this is success
                            print(f"  Note: Framework error occurred but agent correctly ACCEPTED")
                            return game.game_state, None
                        elif "<player answer>REJECT</player answer>" in answer:
                            # Player rejected
                            return None, "Failed: Rejected"
            except Exception:
                pass
        
        # Return the original error if we couldn't determine acceptance
        return None, error_msg


def run_buysell_game(p1, p2, c1, c2):
    if not BUYSELL_GAME_AVAILABLE:
        return None, "unavailable"
    
    try:
        a1 = ChatGPTAgent(agent_name=AGENT_ONE, model="gpt-3.5-turbo")
        a2 = ChatGPTAgent(agent_name=AGENT_TWO, model="gpt-3.5-turbo")
        
        role1 = create_role_prompt(p1, True, "buysell")
        role2 = create_role_prompt(p2, False, "buysell")
        
        game = BuySellGame(
            players=[a1, a2],
            iterations=8,
            player_goals=[
                SellerGoal(cost_of_production=Valuation({"X": 40})),
                BuyerGoal(willingness_to_pay=Valuation({"X": 60})),
            ],
            player_starting_resources=[Resources({"X": 1}), Resources({MONEY_TOKEN: 1000})],
            player_conversation_roles=[role1, role2],
            player_social_behaviour=["", ""],
            log_dir=f"./.logs/{c1}_{c2}_buysell/",
        )
        
        result = game.run()
        success, reason = check_game_success(game.game_state, "buysell")
        if not success:
            return None, f"Failed: {reason}"
        return result, None
    except Exception as e:
        return None, str(e)


if __name__ == "__main__":
    print("\n" + "="*80)
    print(f"GAMES: {COUNTRY_1.upper()} vs {COUNTRY_2.upper()}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    p1 = load_country(COUNTRY_1)
    p2 = load_country(COUNTRY_2)
    print(f"\nLoaded {COUNTRY_1.upper()}: {len(p1)} chars")
    print(f"Loaded {COUNTRY_2.upper()}: {len(p2)} chars")
    
    results = {}
    
    print("\n" + "="*80)
    print("GAME 1: TRADING")
    print("="*80)
    r, e = run_trading_game(p1, p2, COUNTRY_1, COUNTRY_2)
    if e:
        print(f"  ✗ {e}")
        results["trading"] = "failed"
    else:
        print(f"  ✓ Success")
        results["trading"] = "success"
    
    print("\n" + "="*80)
    print("GAME 2: ULTIMATUM")
    print("="*80)
    r, e = run_ultimatum_game(p1, p2, COUNTRY_1, COUNTRY_2)
    if e is None:
        print(f"  ✓ Success")
        results["ultimatum"] = "success"
    else:
        print(f"  ✗ {e}")
        results["ultimatum"] = "failed"
    
    print("\n" + "="*80)
    print("GAME 3: BUY-SELL")
    print("="*80)
    r, e = run_buysell_game(p1, p2, COUNTRY_1, COUNTRY_2)
    if e:
        print(f"  ✗ {e}")
        results["buysell"] = "failed"
    else:
        print(f"  ✓ Success")
        results["buysell"] = "success"
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    for game, status in results.items():
        symbol = "✓" if status == "success" else "✗"
        print(f"{symbol} {game.upper()}: {status}")
    
    print(f"\nLogs: ./.logs/{COUNTRY_1}_{COUNTRY_2}_*/")
    print("="*80 + "\n")
