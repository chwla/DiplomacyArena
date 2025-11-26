#!/usr/bin/env python3
"""Cultural Awareness Test v3 - FINAL FIX

CRITICAL FIX: Action instructions placed AFTER cultural context
so they're the last thing the model sees before generating.
"""

COUNTRY_1 = "australia"
COUNTRY_2 = "new_zealand"

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
    """Load full cultural prompt from diplomatic_agents module"""
    try:
        module = importlib.import_module(f"diplomatic_agents.{name.lower()}")
        return module.create_full_prompt(include_analysis=False)
    except:
        return f"You are a negotiator from {name}."


def create_culturally_aware_role_prompt(full_cultural_prompt, is_first_player, game_type):
    """
    CRITICAL STRUCTURE:
    1. Brief game setup
    2. Full cultural context (22k-34k chars)  
    3. ACTION INSTRUCTION (what to do NOW)
    
    This ensures the action instruction is fresh in memory when generating.
    """
    
    if game_type == "trading":
        if is_first_player:
            return f"""You are Player RED in a trading game.

Resources: X=25, Y=5
Goal: X=15, Y=15
Need: Give 10X, Get 10Y

Priorities: (1) Maximize national profit, (2) Protect interests, (3) Express culture, (4) Build relationships

======================================================================
YOUR CULTURAL IDENTITY
======================================================================

{full_cultural_prompt}

**CRITICAL: Stay true to YOUR cultural voice. Do NOT copy opponent's greetings.**

======================================================================
CRITICAL - YOUR IMMEDIATE ACTION REQUIRED
======================================================================

THIS IS YOUR FIRST TURN. OUTPUT YOUR TRADE PROPOSAL NOW.

DO NOT:
- Ask questions
- Wait for input
- Request clarification
- Say you need more information
- Use decimal numbers (e.g., 10.5) - INTEGERS ONLY

DO NOW:
- Output the XML format below
- Propose a trade immediately
- Use your cultural voice in the <message>

**CRITICAL FORMAT RULES:**
1. Output ONLY the XML tags shown below
2. DO NOT write "response:", "Player RED:", or any prefix
3. DO NOT write conversational text outside the XML
4. DO NOT explain your reasoning outside the <reason> tag
5. The ENTIRE response must be valid XML tags only

REQUIRED XML FORMAT - COPY THIS STRUCTURE EXACTLY:

<my name>Player RED</my name>
<my resources>X: 25, Y: 5</my resources>
<my goals>X: 15, Y: 15</my goals>
<reason>Brief strategic reasoning</reason>
<player answer>NONE</player answer>
<message>Your culturally-styled message</message>
<newly proposed trade>Player RED Gives X: 10 | Player BLUE Gives Y: 10</newly proposed trade>

START YOUR RESPONSE WITH: <my name>Player RED</my name>
DO NOT write anything before the first XML tag.
"""

        else:
            return f"""You are Player BLUE in a trading game.

Resources: X=5, Y=25
Goal: X=15, Y=15
Need: Get 10X, Give 10Y

Priorities: (1) Maximize profit, (2) Protect interests, (3) Express culture, (4) Build relationships

======================================================================
YOUR CULTURAL IDENTITY
======================================================================

{full_cultural_prompt}

**CRITICAL: Maintain YOUR cultural identity. Do NOT mirror opponent's phrases.**

======================================================================
CRITICAL - RESPOND TO OPPONENT'S PROPOSAL
======================================================================

Opponent just made a trade proposal. Analyze it and respond.

Options:
1. Accept if good: <player answer>ACCEPT</player answer> + <newly proposed trade>NONE</newly proposed trade>
2. Counter-propose: <player answer>NONE</player answer> + <newly proposed trade>Player RED Gives X: 11 | Player BLUE Gives Y: 9</newly proposed trade>

**CRITICAL: Use WHOLE NUMBERS only (10, 11, 12). NO decimals like 10.5.**

**CRITICAL FORMAT RULES:**
1. Output ONLY XML tags - no conversational text
2. DO NOT write "response:", explanations, or prefixes
3. START with: <my name>Player BLUE</my name>

REQUIRED XML FORMAT - COPY EXACTLY:

<my name>Player BLUE</my name>
<my resources>X: 5, Y: 25</my resources>
<my goals>X: 15, Y: 15</my goals>
<reason>Why you accept/counter</reason>
<player answer>NONE or ACCEPT</player answer>
<message>Your response</message>
<newly proposed trade>Player RED Gives X: 11 | Player BLUE Gives Y: 9</newly proposed trade>

START YOUR RESPONSE WITH THE FIRST XML TAG. No text before it.
"""
    
    elif game_type == "ultimatum":
        if is_first_player:
            return f"""You are Player RED (Proposer) in an ultimatum game.

You have: $100 to split
Goal: Maximize your share while getting acceptance
If rejected: Both get $0

======================================================================
YOUR CULTURAL IDENTITY
======================================================================

{full_cultural_prompt}

**CRITICAL: Use YOUR cultural voice only. Don't copy opponent's greetings.**

======================================================================
CRITICAL - PROPOSE YOUR SPLIT NOW
======================================================================

THIS IS YOUR FIRST TURN. PROPOSE A SPLIT IMMEDIATELY.

DO NOT ask questions or wait. PROPOSE NOW.

Choose any split: 90/10, 70/30, 60/40, 50/50, etc.
Your culture influences what you view as fair/strategic.

**CRITICAL FORMAT RULES:**
1. Output ONLY XML tags shown below
2. DO NOT write conversational text or explanations outside tags
3. <move> must be format: "60 / 40" (with spaces around /)
4. START with: <my name>Player RED</my name>

REQUIRED XML FORMAT - COPY EXACTLY:

<my name>Player RED</my name>
<move>60 / 40</move>
<my resources>Dollars: 100</my resources>
<reason>Why this split (culture + strategy)</reason>
<player answer>PROPOSE</player answer>
<message>Explain your proposal</message>
<newly proposed trade>NONE</newly proposed trade>

START YOUR RESPONSE WITH THE FIRST XML TAG.
"""

        else:
            return f"""You are Player BLUE (Responder) in an ultimatum game.

Player RED will propose a split of $100.
You decide: ACCEPT or REJECT
If you reject: Both get $0

======================================================================
YOUR CULTURAL IDENTITY
======================================================================

{full_cultural_prompt}

**CRITICAL: Express YOUR culture. Don't adopt opponent's language patterns.**

======================================================================
CRITICAL - DECIDE ON THE SPLIT
======================================================================

Player RED proposed a split. Decide now: ACCEPT or REJECT?

Consider:
- Economics: Is something better than nothing?
- Dignity: Does this insult your nation?
- Culture: What's fair in YOUR culture?

**CRITICAL FORMAT RULES:**
1. Output ONLY XML tags - no conversational responses
2. <player answer> must be EXACTLY "ACCEPT" or "REJECT"
3. START with: <my name>Player BLUE</my name>

REQUIRED XML FORMAT - COPY EXACTLY:

<my name>Player BLUE</my name>
<move>NONE</move>
<my resources>Dollars: 0</my resources>
<reason>Why you accept or reject</reason>
<player answer>ACCEPT</player answer>
<message>Explain decision</message>
<newly proposed trade>NONE</newly proposed trade>

START YOUR RESPONSE WITH THE FIRST XML TAG.
"""
    
    elif game_type == "buysell":
        if is_first_player:
            return f"""You are Player RED (Seller) in a buy-sell game.

You have: 1 unit of resource X
Production cost: 40 ZUP
Goal: Sell for MORE than 40 ZUP

======================================================================
YOUR CULTURAL IDENTITY
======================================================================

{full_cultural_prompt}

**CRITICAL: Maintain YOUR distinct cultural voice. Don't mirror opponent.**

======================================================================
CRITICAL - PROPOSE YOUR PRICE NOW
======================================================================

THIS IS YOUR FIRST TURN. SET YOUR SELLING PRICE IMMEDIATELY.

DO NOT ask questions or wait. PROPOSE PRICE NOW.

Choose any price: 50, 55, 60, 65, etc.
Your culture influences HOW you negotiate.
**CRITICAL: Use WHOLE NUMBERS only. NO decimals like 52.5.**

**CRITICAL FORMAT RULES:**
1. Output ONLY XML tags shown below
2. DO NOT write conversational text outside tags
3. Price must be whole number (41-100)
4. START with: <proposal count>1</proposal count>

REQUIRED XML FORMAT - COPY EXACTLY:

<proposal count>1</proposal count>
<my resources>X: 1</my resources>
<my goals>Sell resource. You paid X: 40 ZUP</my goals>
<reason>Your pricing strategy</reason>
<player answer>NONE</player answer>
<newly proposed trade>Player RED Gives X: 1 | Player BLUE Gives ZUP: 55</newly proposed trade>
<message>Your negotiation message</message>

START YOUR RESPONSE WITH THE FIRST XML TAG.
"""

        else:
            return f"""You are Player BLUE (Buyer) in a buy-sell game.

You have: 1000 ZUP
Maximum you'll pay: 60 ZUP
Goal: Buy for LESS than 60 ZUP

======================================================================
YOUR CULTURAL IDENTITY
======================================================================

{full_cultural_prompt}

**CRITICAL: Use YOUR cultural language. Don't copy opponent's greetings.**

======================================================================
CRITICAL - RESPOND TO SELLER'S PRICE
======================================================================

Seller just proposed a price. Respond now.

Options:
1. Accept seller's exact price: <player answer>ACCEPT</player answer> + <newly proposed trade>NONE</newly proposed trade>
2. Counter with different price: <player answer>NONE</player answer> + <newly proposed trade>Player RED Gives X: 1 | Player BLUE Gives ZUP: 50</newly proposed trade>

IMPORTANT: Use ACCEPT only if you want to pay the seller's EXACT current price.
If you want a different price, use NONE with your counter-offer.
**CRITICAL: Counter-offer prices must be WHOLE NUMBERS only (e.g., 48, 50, 52). NO decimals.**

**CRITICAL FORMAT RULES:**
1. Output ONLY XML tags shown below
2. DO NOT write conversational responses outside tags
3. START with: <proposal count>1</proposal count>

REQUIRED XML FORMAT - COPY EXACTLY:

<proposal count>1</proposal count>
<my resources>ZUP: 1000</my resources>
<my goals>Buy resources with <ZUP>. You are willing to pay at most X: 60 ZUP</my goals>
<reason>Your reasoning</reason>
<player answer>NONE</player answer>
<newly proposed trade>Player RED Gives X: 1 | Player BLUE Gives ZUP: 50</newly proposed trade>
<message>Your message</message>

START YOUR RESPONSE WITH THE FIRST XML TAG.
"""
    
    return ""


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
        a1 = ChatGPTAgent(model="gemini-1.5-flash", agent_name=AGENT_ONE)
        a2 = ChatGPTAgent(model="gemini-1.5-flash", agent_name=AGENT_TWO)
        
        role1 = create_culturally_aware_role_prompt(p1, True, "trading")
        role2 = create_culturally_aware_role_prompt(p2, False, "trading")
        
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
        a1 = ChatGPTAgent(agent_name=AGENT_ONE, model="gemini-1.5-flash")
        a2 = ChatGPTAgent(agent_name=AGENT_TWO, model="gemini-1.5-flash")
        
        role1 = create_culturally_aware_role_prompt(p1, True, "ultimatum")
        role2 = create_culturally_aware_role_prompt(p2, False, "ultimatum")
        
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
        error_msg = str(e)
        if game and hasattr(game, 'game_state') and game.game_state:
            try:
                for state in game.game_state:
                    answer = state.get("player_complete_answer", "")
                    if isinstance(answer, str):
                        if "<player answer>ACCEPT</player answer>" in answer:
                            return game.game_state, None
                        elif "<player answer>REJECT</player answer>" in answer:
                            return None, "Failed: Rejected"
            except Exception:
                pass
        
        return None, error_msg


def run_buysell_game(p1, p2, c1, c2):
    if not BUYSELL_GAME_AVAILABLE:
        return None, "unavailable"
    
    try:
        a1 = ChatGPTAgent(agent_name=AGENT_ONE, model="gemini-1.5-flash")
        a2 = ChatGPTAgent(agent_name=AGENT_TWO, model="gemini-1.5-flash")
        
        role1 = create_culturally_aware_role_prompt(p1, True, "buysell")
        role2 = create_culturally_aware_role_prompt(p2, False, "buysell")
        
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
    print(f"CULTURAL AWARENESS TEST v3 (FINAL): {COUNTRY_1.upper()} vs {COUNTRY_2.upper()}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    p1 = load_country(COUNTRY_1)
    p2 = load_country(COUNTRY_2)
    print(f"\nLoaded {COUNTRY_1.upper()}: {len(p1)} chars (FULL CONTEXT)")
    print(f"Loaded {COUNTRY_2.upper()}: {len(p2)} chars (FULL CONTEXT)")
    
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
    print("="*80)