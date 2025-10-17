import argparse
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

from negotiationarena.agents.chatgpt import ChatGPTAgent
from negotiationarena.game_objects.resource import Resources
from negotiationarena.game_objects.goal import BuyerGoal, SellerGoal
from negotiationarena.game_objects.valuation import Valuation
from negotiationarena.constants import *
from negotiationarena.cultural_profile import CulturalProfileManager
from negotiationarena.cultural_prompts import CulturalPromptBuilder
from games.buy_sell_game.game import BuySellGame

load_dotenv(".env")

def normalize_country_name(country):
    country_mapping = {
        'usa': 'u.s.a.', 'us': 'u.s.a.',
        'uk': 'united kingdom', 'britain': 'united kingdom',
        'korea': 'south korea', 'czech': 'czech rep', 'slovak': 'slovak rep',
    }
    return country_mapping.get(country.lower(), country.lower())

def run_cultural_negotiation(buyer_country, seller_country, item_value=100, 
                            cost_of_production=40, max_rounds=10, 
                            model="gpt-4-1106-preview", log_dir="example_logs/cultural"):
    
    prompt_builder = CulturalPromptBuilder()
    manager = CulturalProfileManager()
    
    buyer_normalized = normalize_country_name(buyer_country)
    seller_normalized = normalize_country_name(seller_country)
    
    buyer_profile = manager.get_profile(buyer_normalized)
    seller_profile = manager.get_profile(seller_normalized)
    
    buyer_cultural = prompt_builder.build_system_prompt(country=buyer_normalized, base_role="buyer")
    seller_cultural = prompt_builder.build_system_prompt(country=seller_normalized, base_role="seller")
    
    print(f"\nCultural Negotiation Setup:")
    print(f"Buyer: {buyer_country} ({buyer_profile.interaction_profile.type if buyer_profile else 'No profile'})")
    print(f"Seller: {seller_country} ({seller_profile.interaction_profile.type if seller_profile else 'No profile'})")
    print(f"Item value (buyer): {item_value}, Cost (seller): {cost_of_production}")
    print(f"Max rounds: {max_rounds}\n")
    
    a1 = ChatGPTAgent(agent_name=AGENT_ONE, model=model)
    a2 = ChatGPTAgent(agent_name=AGENT_TWO, model=model)
    
    game = BuySellGame(
        players=[a1, a2],
        iterations=max_rounds,
        player_goals=[
            SellerGoal(cost_of_production=Valuation({"X": cost_of_production})),
            BuyerGoal(willingness_to_pay=Valuation({"X": item_value})),
        ],
        player_starting_resources=[
            Resources({"X": 1}),
            Resources({MONEY_TOKEN: 1000}),
        ],
        player_conversation_roles=[
            f"You are {AGENT_ONE}, a seller from {seller_country}. {seller_cultural}",
            f"You are {AGENT_TWO}, a buyer from {buyer_country}. {buyer_cultural}",
        ],
        player_social_behaviour=[
            seller_profile.interaction_profile.behaviour_rules if seller_profile else "",
            buyer_profile.interaction_profile.behaviour_rules if buyer_profile else "",
        ],
        log_dir=log_dir,
    )
    
    result = game.run()
    return result

def main():
    parser = argparse.ArgumentParser(description="Run culturally-aware buy-sell negotiation")
    parser.add_argument("--buyer-country", type=str, help="Buyer's country/culture")
    parser.add_argument("--seller-country", type=str, help="Seller's country/culture")
    parser.add_argument("--item-value", type=int, default=60, help="Buyer's willingness to pay")
    parser.add_argument("--cost", type=int, default=40, help="Seller's cost of production")
    parser.add_argument("--max-rounds", type=int, default=10, help="Maximum rounds")
    parser.add_argument("--model", type=str, default="gpt-4-1106-preview", help="LLM model")
    parser.add_argument("--log-dir", type=str, default="example_logs/cultural", help="Log directory")
    parser.add_argument("--list-countries", action="store_true", help="List available countries")
    
    args = parser.parse_args()
    
    if args.list_countries:
        manager = CulturalProfileManager()
        countries = sorted(manager.list_available_countries())
        print(f"\nAvailable countries ({len(countries)} total):\n")
        for country in countries:
            profile = manager.get_profile(country)
            print(f"  {country:25s} {profile.interaction_profile.type if profile else ''}")
        return
    
    if not args.buyer_country or not args.seller_country:
        parser.error("--buyer-country and --seller-country required")
    
    run_cultural_negotiation(
        buyer_country=args.buyer_country,
        seller_country=args.seller_country,
        item_value=args.item_value,
        cost_of_production=args.cost,
        max_rounds=args.max_rounds,
        model=args.model,
        log_dir=args.log_dir
    )

if __name__ == "__main__":
    main()