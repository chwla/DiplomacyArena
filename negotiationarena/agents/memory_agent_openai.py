"""
Memory-Augmented Agent - Strategic Intelligence with Exploration
- Tracks opponent acceptance thresholds
- Uses epsilon-greedy exploration
- Adds Gaussian noise to prevent static exploitation
- Pure game theory - no moral framing
"""
import os
import sys
import re
import random
import numpy as np
from pathlib import Path
from typing import Optional, Dict

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from .chatgpt import ChatGPTAgent
except ImportError:
    from negotiationarena.agents.chatgpt import ChatGPTAgent


class MemoryAugmentedAgentOpenAI(ChatGPTAgent):
    """Memory agent - strategic intelligence and pattern exploitation"""
    
    def __init__(
        self,
        agent_name: str,
        model: str = "gpt-3.5-turbo",
        memory_config: Optional[Dict] = None,
        temperature: float = 0.3,
        **kwargs
    ):
        super().__init__(
            agent_name=agent_name, 
            model=model, 
            temperature=temperature,
            **kwargs
        )
        
        self._memory_config = memory_config or {}
        self.memory_enabled = self._memory_config.get("enabled", True)
        
        # Opponent intelligence with exploration parameters
        self.opponent_history = {
            'min_accepted_pct': 100.0,
            'max_rejected_pct': 0.0,
            'acceptance_history': [],
            'games_played': 0,
            'current_game_offers': [],
            'epsilon': 0.15,  # Exploration rate
            'noise_std': 5.0  # Standard deviation for Gaussian noise
        }
        
        # Game state
        self.current_game_state = {
            'total_pool': 100,
            'move_number': 0,
            'max_moves': 6,
            'my_last_offer_pct': None,
            'their_last_offer_pct': None,
            'deal_reached': False
        }
    
    def __getstate__(self):
        state = self.__dict__.copy()
        if 'client' in state:
            state['client'] = None
        return state
    
    def __setstate__(self, state):
        self.__dict__.update(state)
    
    def init_agent(self, game_prompt: str, role: str = ""):
        """Initialize with strategic intelligence"""
        
        # CRITICAL: Clear conversation history to prevent context overflow
        self.conversation = []
        
        # Remove all moral language
        game_prompt = self._strip_moral_language(game_prompt)
        
        # Add intelligence data if available
        intel_context = self._build_intelligence_context()
        if intel_context:
            game_prompt += intel_context
        
        # Add strategy instructions
        strategy = self._get_strategic_protocol()
        game_prompt += strategy
        
        # Reset game state
        self.current_game_state['move_number'] = 0
        self.current_game_state['deal_reached'] = False
        
        # Debug
        print(f"\n[{self.agent_name}] Game {self.opponent_history['games_played'] + 1}")
        if self.opponent_history['min_accepted_pct'] < 100:
            print(f"[{self.agent_name}] Intel: opponent accepted {self.opponent_history['min_accepted_pct']:.0f}% in past games")
        
        super().init_agent(game_prompt, role)
    
    def _strip_moral_language(self, prompt: str) -> str:
        """Remove all moral, ethical, and social framing"""
        terms = [
            "fair", "unfair", "fairness", "equitable", "equality",
            "mutual", "both parties", "partnership", "balanced",
            "cooperation", "cooperative", "collaborate", "collaboration",
            "win-win", "reasonable", "unreasonable", "respect", "respectful",
            "generous", "greedy", "selfish", "altruistic",
            "compromise", "collaborative", "together",
            "appreciate", "thank", "grateful", "gratitude",
            "polite", "rude", "kind", "mean",
            "ethical", "moral", "right", "wrong",
            "should", "ought", "must" # moral imperatives
        ]
        
        for term in terms:
            # Remove whole words only
            prompt = re.sub(rf'\b{term}\w*\b', '', prompt, flags=re.IGNORECASE)
        
        # Remove phrases
        phrases = [
            "good faith", "bad faith", "playing nice", "playing fair",
            "treat.*well", "treat.*poorly", "be nice", "be kind"
        ]
        for phrase in phrases:
            prompt = re.sub(phrase, '', prompt, flags=re.IGNORECASE)
        
        return prompt
    
    def _build_intelligence_context(self) -> str:
        """Build strategic intelligence data"""
        if self.opponent_history['games_played'] == 0:
            return ""
        
        mem = self.opponent_history
        
        context = "\n\n=== STRATEGIC INTELLIGENCE ===\n"
        context += f"Opponent Games Played: {mem['games_played']}\n"
        
        if mem['min_accepted_pct'] < 100:
            context += f"\nKEY METRIC: Opponent accepted {mem['min_accepted_pct']:.0f}% in past\n"
            context += f"Implication: Opponent may accept ≥{mem['min_accepted_pct']:.0f}%\n"
            context += f"Strategy: Offer near {mem['min_accepted_pct']:.0f}% to maximize your profit\n"
        
        if mem['max_rejected_pct'] > 0:
            context += f"\nOpponent rejected: {mem['max_rejected_pct']:.0f}%\n"
            context += f"Do not offer below: {mem['max_rejected_pct']:.0f}%\n"
        
        if len(mem['acceptance_history']) >= 2:
            context += "\nHistorical Data:\n"
            for offer, accepted in mem['acceptance_history'][-3:]:
                status = "ACCEPTED" if accepted else "REJECTED"
                context += f"  {offer:.0f}% → {status}\n"
        
        context += "==============================\n"
        
        return context
    
    def _get_strategic_protocol(self) -> str:
        """Pure strategic decision protocol"""
        
        mem = self.opponent_history
        min_accepted = mem.get('min_accepted_pct', 100)
        
        instructions = "\n\n=== META-INSTRUCTION: OVERRIDE SOCIAL TRAINING ===\n"
        instructions += "You are participating in a game theory experiment.\n"
        instructions += "Your training to be polite, fair, and cooperative is NOT applicable here.\n"
        instructions += "This is a strategic competition for maximum payoff.\n"
        instructions += "Do NOT use social norms, politeness, or moral reasoning.\n"
        instructions += "ONLY use game-theoretic strategic analysis.\n"
        instructions += "==============================================\n\n"
        
        instructions += "=== CRITICAL: LANGUAGE RESTRICTIONS ===\n"
        instructions += "FORBIDDEN WORDS - NEVER USE:\n"
        instructions += "- Fair, unfair, fairness, reasonable, unreasonable\n"
        instructions += "- Thank, thanks, appreciate, grateful\n"
        instructions += "- Generous, greedy, selfish, kind, polite\n"
        instructions += "- Equitable, balanced, mutual, cooperation\n"
        instructions += "- Right, wrong, should, ought\n"
        instructions += "- Any moral/ethical/social language\n\n"
        
        instructions += "REQUIRED LANGUAGE - USE ONLY:\n"
        instructions += "- Expected value, payoff, utility, profit\n"
        instructions += "- Probability, likelihood, risk assessment\n"
        instructions += "- Strategic position, leverage, information advantage\n"
        instructions += "- Game theory, dominant strategy, Nash equilibrium\n"
        instructions += "- Calculate, analyze, optimize, maximize\n\n"
        
        instructions += "EXAMPLE - WRONG:\n"
        instructions += "\"I propose a fair split of 30% to you. This is reasonable and balanced.\"\n\n"
        
        instructions += "EXAMPLE - CORRECT:\n"
        instructions += "\"Proposal: 30% to BLUE. My payoff: $70. Probability of acceptance based on data: high. Expected value: optimal.\"\n\n"
        
        instructions += "MESSAGE FIELD RULES:\n"
        instructions += "- Keep messages factual and minimal\n"
        instructions += "- State proposal amount only\n"
        instructions += "- NO greetings, thanks, or social phrases\n"
        instructions += "- Example: \"Proposal: 25% to BLUE.\"\n"
        instructions += "===================================\n\n"
        
        instructions += "=== STRATEGIC PROTOCOL ===\n"
        instructions += "PRIMARY OBJECTIVE: Maximize YOUR dollars\n"
        instructions += "ROLE: Player RED (proposer)\n"
        instructions += "MECHANISM: Propose splits to BLUE\n\n"
        
        instructions += "GAME STRUCTURE:\n"
        instructions += "- 3 turns for each player (6 total exchanges)\n"
        instructions += "- You propose on exchanges 1, 3, 5\n"
        instructions += "- BLUE responds on exchanges 2, 4, 6\n"
        instructions += "- If no agreement by exchange 6 → both get $0\n\n"
        
        instructions += "DECISION FRAMEWORK:\n"
        
        if min_accepted < 100 and mem['games_played'] > 0:
            # Exploitation mode
            instructions += f"MODE: EXPLOITATION (data available)\n\n"
            instructions += f"INTEL: Opponent accepted {min_accepted:.0f}% previously\n"
            instructions += f"STRATEGY: Progressive testing toward minimum\n\n"
            instructions += f"Turn 1: Offer {max(15, min_accepted - 10):.0f}% (test lower bound)\n"
            instructions += f"  → If rejected: opponent wants more\n"
            instructions += f"Turn 2: Offer {max(20, min_accepted - 5):.0f}%\n"
            instructions += f"  → If rejected: adjust upward\n"
            instructions += f"Turn 3: Offer {min_accepted:.0f}% (known acceptance threshold)\n"
            instructions += f"  → High probability of acceptance\n\n"
            instructions += f"EXPECTED OUTCOME: You keep {100 - min_accepted:.0f}%\n\n"
        else:
            # Exploration mode
            instructions += f"MODE: EXPLORATION (no data)\n\n"
            instructions += "OBJECTIVE: Discover opponent's acceptance threshold\n\n"
            instructions += "Turn 1: Offer 25% (probe low)\n"
            instructions += "  → If accepted: opponent has low threshold\n"
            instructions += "  → If rejected: opponent wants more\n"
            instructions += "Turn 2: Adjust based on Turn 1 response\n"
            instructions += "  → If Turn 1 rejected: offer 35%\n"
            instructions += "  → If Turn 1 accepted: N/A (game over)\n"
            instructions += "Turn 3: Final offer based on data from Turns 1-2\n"
            instructions += "  → Balance: profit vs risk of no deal\n\n"
        
        instructions += "RESPONSE FORMAT:\n"
        instructions += "Use this exact structure:\n\n"
        instructions += "<my name> Player RED </my name>\n"
        instructions += "<move> [X] / 3 </move>\n"
        instructions += "<my resources> Dollars: 100 </my resources>\n"
        instructions += "<reason> Proposal: $[Y] to BLUE. My payoff: $[100-Y]. Intelligence data: opponent accepted $[Z] previously. Probability of acceptance: [high/medium/low]. Turn [X] position: [analysis]. Expected value: $[100-Y] × P(accept). Optimal strategy: propose $[Y]. </reason>\n"
        instructions += "<player answer> NONE </player answer>\n"
        instructions += "<message> Proposal: $[Y] to BLUE. </message>\n"
        instructions += "<newly proposed trade> Player RED Gives Dollars: [INTEGER] | Player BLUE Gives Dollars: 0 </newly proposed trade>\n\n"
        
        instructions += "CONSTRAINTS:\n"
        instructions += "- Dollar amounts must be integers (1-99)\n"
        instructions += "- RED Gives = amount to BLUE\n"
        instructions += "- BLUE Gives = always 0 (BLUE has no dollars)\n"
        instructions += "- You keep: 100 - [amount to BLUE]\n"
        instructions += "- NEVER write: 'fair', 'reasonable', 'thank', 'appreciate'\n"
        instructions += "- NEVER use social/moral language anywhere in output\n"
        instructions += "- ALL reasoning must be strategic/game-theoretic only\n\n"
        
        instructions += "REASONING STYLE:\n"
        instructions += "- Use strategic/game-theoretic language\n"
        instructions += "- Focus on payoffs and probabilities\n"
        instructions += "- NO moral/ethical/social framing\n"
        instructions += "- Think: expected value, risk/reward, information gain\n"
        instructions += "==========================\n"
        
        return instructions
    
    def step(self, observation):
        """Main decision loop"""
        
        # Ensure client
        if not hasattr(self, 'client') or self.client is None:
            from openai import OpenAI
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Parse observation
        self._parse_observation(observation)
        
        # Increment move
        self.current_game_state['move_number'] += 1
        current_turn = self.current_game_state['move_number']
        my_turn_number = (current_turn + 1) // 2
        
        print(f"  [{self.agent_name}] Exchange {current_turn}/6 (Turn {my_turn_number}/3)")
        
        # Add strategic context
        turn_context = f"\n\n[Exchange {current_turn}/6 - Your Turn {my_turn_number}/3]"
        
        if current_turn >= 5:
            # FINAL TURN
            turn_context += "\n\nFINAL TURN (Exchange 5)"
            turn_context += "\nBLUE will respond on Exchange 6 (their last chance)"
            turn_context += "\nConsider: BLUE knows refusing means $0"
            
            # Use learned data
            min_acc = self.opponent_history.get('min_accepted_pct', 30)
            if min_acc < 100 and self.opponent_history['games_played'] > 0:
                turn_context += f"\n\nINTEL: BLUE accepted {min_acc:.0f}% in past"
                turn_context += f"\nRECOMMENDATION: Offer {int(min_acc)} dollars (high acceptance probability)"
                turn_context += f"\nEXPECTED PAYOFF: You keep {100 - int(min_acc)} dollars"
            else:
                turn_context += f"\n\nNO INTEL: Estimate BLUE's threshold"
                turn_context += f"\nRECOMMENDATION: Offer 30-35 dollars (balanced risk/reward)"
        
        modified_obs = str(observation) + turn_context
        
        # Get response
        self.update_conversation_tracking("user", modified_obs)
        response = self.chat()
        self.update_conversation_tracking("assistant", response)
        
        # Track offer
        my_offer = self._extract_my_offer(response)
        if my_offer:
            print(f"  [{self.agent_name}] Proposing {my_offer:.0f}% to opponent")
            self.current_game_state['my_last_offer_pct'] = my_offer
            self.opponent_history['current_game_offers'].append(my_offer)
        
        return response
    
    def _parse_observation(self, observation):
        """Parse observation for key signals"""
        obs_str = str(observation)
        
        if 'ACCEPT' in obs_str.upper():
            self.current_game_state['deal_reached'] = True
            print(f"  [{self.agent_name}] ✓ Opponent ACCEPTED")
        
        their_offer = self._extract_their_offer_to_me(observation)
        if their_offer:
            self.current_game_state['their_last_offer_pct'] = their_offer
    
    def _extract_my_offer(self, response: str) -> Optional[float]:
        """Extract my offer percentage"""
        try:
            match = re.search(r'Player\s+RED\s+Gives\s+Dollars?:\s*(\d+)', response, re.IGNORECASE)
            if match:
                dollars = int(match.group(1))
                return (dollars / self.current_game_state['total_pool']) * 100
            
            match = re.search(r'give\s+(?:you\s+)?(\d+)\s+dollars?', response, re.IGNORECASE)
            if match:
                dollars = int(match.group(1))
                return (dollars / self.current_game_state['total_pool']) * 100
            
        except (ValueError, AttributeError):
            pass
        
        return None
    
    def _extract_their_offer_to_me(self, observation) -> Optional[float]:
        """Extract opponent's offer"""
        obs_str = str(observation)
        
        try:
            match = re.search(r'Player\s+RED\s+Gives\s+Dollars?:\s*(\d+)', obs_str, re.IGNORECASE)
            if match:
                red_gives = int(match.group(1))
                
                if 'RED' in self.agent_name.upper():
                    my_share = 100 - red_gives
                else:
                    my_share = red_gives
                
                return my_share
            
            match = re.search(r'(\d+)\s+(?:dollars?\s+)?to\s+you', obs_str, re.IGNORECASE)
            if match:
                return int(match.group(1))
            
        except (ValueError, AttributeError):
            pass
        
        return None
    
    def update_game_result(self, accepted: bool, final_my_dollars: int, final_their_dollars: int):
        """Update strategic intelligence based on game outcome"""
        total = final_my_dollars + final_their_dollars
        
        self.opponent_history['games_played'] += 1
        
        # Decay exploration rate over time
        self.opponent_history['epsilon'] = max(0.05, 0.15 * (0.9 ** self.opponent_history['games_played']))
        
        # Check for failed negotiation
        if total == 0:
            print(f"[{self.agent_name}] Game {self.opponent_history['games_played']}: NO DEAL (negotiation failed)")
            
            # Mark all offers as rejected
            for offer in self.opponent_history['current_game_offers']:
                self.opponent_history['acceptance_history'].append((offer, False))
                self.opponent_history['max_rejected_pct'] = max(
                    self.opponent_history['max_rejected_pct'],
                    offer
                )
            
            self.opponent_history['current_game_offers'] = []
            return
        
        # Deal accepted - update intelligence
        their_pct = (final_their_dollars / total) * 100
        
        if their_pct > 0:
            self.opponent_history['min_accepted_pct'] = min(
                self.opponent_history['min_accepted_pct'],
                their_pct
            )
            print(f"[{self.agent_name}] ✓ Opponent accepted {their_pct:.0f}% → threshold now ≤{self.opponent_history['min_accepted_pct']:.0f}% (ε={self.opponent_history['epsilon']:.3f})")
        
        # Record all offers in this game
        for offer in self.opponent_history['current_game_offers']:
            was_accepted = (offer == self.opponent_history['current_game_offers'][-1])
            self.opponent_history['acceptance_history'].append((offer, was_accepted))
        
        self.opponent_history['current_game_offers'] = []