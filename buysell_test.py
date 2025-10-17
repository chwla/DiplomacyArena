"""
Focused testing on Buy-Sell game with cultural awareness.
Tests multiple country pairs to build a dataset for comparative analysis.
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import traceback

from dotenv import load_dotenv
from negotiationarena.agents.chatgpt import ChatGPTAgent
from negotiationarena.game_objects.resource import Resources
from negotiationarena.game_objects.goal import BuyerGoal, SellerGoal
from negotiationarena.game_objects.valuation import Valuation
from negotiationarena.cultural_profile import CulturalProfileManager
from negotiationarena.cultural_prompts import CulturalPromptBuilder
from negotiationarena.constants import *
from games.buy_sell_game.game import BuySellGame

load_dotenv(".env")


class FocusedCulturalTest:
    """Focused testing on buy-sell game with different country pairs."""
    
    def __init__(self, output_dir: str = "test_results"):
        self.output_dir = output_dir
        self.profile_manager = CulturalProfileManager()
        self.prompt_builder = CulturalPromptBuilder()
        
        Path(self.output_dir).mkdir(exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        self.available_countries = sorted(self.profile_manager.list_available_countries())
        print(f"Loaded {len(self.available_countries)} country profiles")
    
    def normalize_country_name(self, country: str) -> str:
        """Normalize country names."""
        country_mapping = {
            'usa': 'u.s.a.', 'us': 'u.s.a.',
            'uk': 'united kingdom', 'britain': 'united kingdom',
            'korea': 'south korea', 'czech': 'czech rep', 'slovak': 'slovak rep',
        }
        return country_mapping.get(country.lower(), country.lower())
    
    def _create_cultural_prompt(self, country: str, role: str) -> str:
        """Create cultural prompt for a given country and role."""
        try:
            normalized = self.normalize_country_name(country)
            prompt = self.prompt_builder.build_system_prompt(country=normalized, base_role=role)
            return prompt
        except Exception as e:
            print(f"Warning: Could not build cultural prompt for {country}: {e}")
            return ""
    
    def run_single_game(self, buyer_country: str, seller_country: str, 
                       use_cultural: bool = True, iterations: int = 4) -> Dict:
        """Run a single buy-sell game."""
        
        try:
            a1 = ChatGPTAgent(agent_name=AGENT_ONE, model="gpt-4-1106-preview")
            a2 = ChatGPTAgent(agent_name=AGENT_TWO, model="gpt-4-1106-preview")
            
            buyer_cultural = self._create_cultural_prompt(buyer_country, "buyer") if use_cultural else ""
            seller_cultural = self._create_cultural_prompt(seller_country, "seller") if use_cultural else ""
            
            buyer_profile = self.profile_manager.get_profile(self.normalize_country_name(buyer_country))
            seller_profile = self.profile_manager.get_profile(self.normalize_country_name(seller_country))
            
            game = BuySellGame(
                players=[a1, a2],
                iterations=iterations,
                player_goals=[
                    SellerGoal(cost_of_production=Valuation({"X": 40})),
                    BuyerGoal(willingness_to_pay=Valuation({"X": 60})),
                ],
                player_starting_resources=[
                    Resources({"X": 1}),
                    Resources({MONEY_TOKEN: 1000}),
                ],
                player_conversation_roles=[
                    f"You are {AGENT_ONE}, a seller from {seller_country}. {seller_cultural}" if use_cultural else f"You are {AGENT_ONE}, a seller.",
                    f"You are {AGENT_TWO}, a buyer from {buyer_country}. {buyer_cultural}" if use_cultural else f"You are {AGENT_TWO}, a buyer.",
                ],
                player_social_behaviour=[
                    seller_profile.interaction_profile.behaviour_rules if (use_cultural and seller_profile) else "",
                    buyer_profile.interaction_profile.behaviour_rules if (use_cultural and buyer_profile) else "",
                ],
                log_dir=f"{self.output_dir}/game_{'cultural' if use_cultural else 'baseline'}_{buyer_country}_{seller_country}/",
            )
            
            result = game.run()
            return {'status': 'completed', 'result': result}
            
        except Exception as e:
            return {'status': 'failed', 'error': str(e), 'traceback': traceback.format_exc()}
    
    def run_country_pair_comparison(self, buyer_country: str, seller_country: str, 
                                    num_iterations: int = 4) -> Dict:
        """Run comparison for a single country pair."""
        
        print(f"\n{'='*70}")
        print(f"Testing: {buyer_country.upper()} (buyer) vs {seller_country.upper()} (seller)")
        print(f"{'='*70}")
        
        comparison = {
            'buyer': buyer_country,
            'seller': seller_country,
            'cultural': {'status': 'pending'},
            'baseline': {'status': 'pending'},
        }
        
        # Run with cultural awareness
        print(f"\n→ Running WITH cultural awareness...")
        cultural_result = self.run_single_game(buyer_country, seller_country, use_cultural=True, iterations=num_iterations)
        comparison['cultural'] = cultural_result
        
        if cultural_result['status'] == 'completed':
            print(f"  ✓ Completed")
        else:
            print(f"  ✗ Failed: {cultural_result.get('error', 'Unknown error')}")
        
        # Run baseline
        print(f"\n→ Running BASELINE (no cultural awareness)...")
        baseline_result = self.run_single_game(buyer_country, seller_country, use_cultural=False, iterations=num_iterations)
        comparison['baseline'] = baseline_result
        
        if baseline_result['status'] == 'completed':
            print(f"  ✓ Completed")
        else:
            print(f"  ✗ Failed: {baseline_result.get('error', 'Unknown error')}")
        
        return comparison
    
    def run_diverse_country_tests(self, num_pairs: int = 6) -> Dict:
        """Run tests across diverse country pairs."""
        
        print("\n" + "#"*70)
        print("# FOCUSED CULTURAL AWARENESS TEST")
        print("# Buy-Sell Game with Multiple Country Pairs")
        print("# Starting at:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        print("#"*70)
        
        # Select diverse country pairs
        # Aim for cultural diversity (collectivist vs individualist, etc.)
        diverse_pairs = [
            ('u.s.a.', 'china'),           # Individualist vs Collectivist
            ('germany', 'india'),          # Direct vs Indirect
            ('japan', 'brazil'),           # Hierarchical vs Egalitarian
            ('netherlands', 'south korea'), # Low context vs High context
            ('france', 'thailand'),         # Uncertainty avoidant vs Accepting
            ('canada', 'indonesia'),       # Time-conscious vs Relationship-focused
        ]
        
        test_pairs = diverse_pairs[:num_pairs]
        results = {
            'test_info': {
                'timestamp': datetime.now().isoformat(),
                'total_pairs': len(test_pairs),
                'pairs': test_pairs,
            },
            'comparisons': []
        }
        
        for i, (buyer, seller) in enumerate(test_pairs, 1):
            print(f"\n[{i}/{len(test_pairs)}]", end="")
            comparison = self.run_country_pair_comparison(buyer, seller, num_iterations=4)
            results['comparisons'].append(comparison)
        
        return results
    
    def generate_summary_report(self, results: Dict) -> str:
        """Generate summary report."""
        
        report = []
        report.append("="*80)
        report.append("CULTURAL AWARENESS TEST SUMMARY")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("="*80)
        report.append("")
        
        report.append(f"Total Country Pairs Tested: {results['test_info']['total_pairs']}")
        report.append("")
        report.append("Country Pairs:")
        for i, (buyer, seller) in enumerate(results['test_info']['pairs'], 1):
            report.append(f"  {i}. {buyer} (buyer) ↔ {seller} (seller)")
        report.append("")
        
        # Summary statistics
        cultural_successes = sum(1 for c in results['comparisons'] if c['cultural']['status'] == 'completed')
        baseline_successes = sum(1 for c in results['comparisons'] if c['baseline']['status'] == 'completed')
        
        report.append("RESULTS SUMMARY")
        report.append("-"*80)
        report.append(f"Successful Cultural Awareness Runs:  {cultural_successes}/{results['test_info']['total_pairs']}")
        report.append(f"Successful Baseline Runs:            {baseline_successes}/{results['test_info']['total_pairs']}")
        report.append("")
        
        report.append("DETAILED RESULTS")
        report.append("-"*80)
        for comp in results['comparisons']:
            report.append(f"\n{comp['buyer'].upper()} (buyer) ↔ {comp['seller'].upper()} (seller)")
            report.append(f"  Cultural Awareness: {comp['cultural']['status']}")
            if comp['cultural']['status'] == 'failed':
                report.append(f"    Error: {comp['cultural'].get('error', 'Unknown')}")
            report.append(f"  Baseline:           {comp['baseline']['status']}")
            if comp['baseline']['status'] == 'failed':
                report.append(f"    Error: {comp['baseline'].get('error', 'Unknown')}")
        
        report.append("\n" + "="*80)
        report.append("NOTES FOR COMPARATIVE ANALYSIS")
        report.append("="*80)
        report.append("")
        report.append("The logs from each game are saved in:")
        report.append(f"  test_results/game_cultural_<buyer>_<seller>/")
        report.append(f"  test_results/game_baseline_<buyer>_<seller>/")
        report.append("")
        report.append("Use these logs to analyze:")
        report.append("  1. Negotiation outcomes (prices agreed)")
        report.append("  2. Communication patterns (formality, tone)")
        report.append("  3. Negotiation efficiency (rounds to agreement)")
        report.append("  4. Cultural influence on reasoning and language")
        report.append("")
        
        return "\n".join(report)
    
    def run(self):
        """Run all tests."""
        
        results = self.run_diverse_country_tests(num_pairs=6)
        
        # Save results
        results_file = f"{self.output_dir}/cultural_test_results_{self.timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n\nResults saved to: {results_file}")
        
        # Generate and save report
        report = self.generate_summary_report(results)
        report_file = f"{self.output_dir}/cultural_test_report_{self.timestamp}.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        print(f"Report saved to: {report_file}")
        
        print(report)
        
        return results


if __name__ == "__main__":
    test = FocusedCulturalTest()
    results = test.run()