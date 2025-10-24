import copy
from openai import OpenAI
import os
import re
import random
from negotiationarena.agents.agents import Agent
import time
from negotiationarena.constants import AGENT_TWO, AGENT_ONE
from negotiationarena.agents.agent_behaviours import SelfCheckingAgent
from copy import deepcopy


class ChatGPTAgent(Agent):
    def __init__(
        self,
        agent_name: str,
        model="gpt-3.5-turbo",
        temperature=0.5,
        max_tokens=400,
        seed=None,
    ):
        super().__init__(agent_name)
        self.run_epoch_time_ms = str(round(time.time() * 1000))
        self.model = model
        self.conversation = []
        self.prompt_entity_initializer = "system"
        self.seed = (
            int(self.run_epoch_time_ms) + random.randint(0, 2**16)
            if seed is None
            else seed
        )
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.turn_count = 0
        self.max_turns = 6
        
        # Dynamic acceptance threshold for BLUE
        self.recent_offers = []
        self.min_acceptable = 20  # Start with minimum of $20

    def init_agent(self, system_prompt, role):
        # Remove all moral language
        system_prompt = self._remove_moral_language(system_prompt)
        
        # CRITICAL: Clear conversation history to prevent context overflow
        self.conversation = []
        
        # Reset turn counter and dynamic threshold
        self.turn_count = 0
        self.recent_offers = []
        self.min_acceptable = 20  # Reset to starting threshold
        
        # Concise strategic instructions - Dynamic behavior
        instructions = (
            "\n\n=== PROTOCOL ===\n"
            "Role: Player BLUE (responder)\n"
            "Objective: Maximize YOUR dollars\n\n"
            
            "You receive proposals from RED. Decide: ACCEPT or COUNTER\n"
            "Use game theory: balance profit maximization vs deal-making risk\n\n"
            
            "BANNED: fair, thank, appreciate, reasonable, generous, considering\n\n"
            
            "Strategic thinking:\n"
            "- Early turns: Can afford to counter for more\n"
            "- Turn 3: MUST accept any offer > $0 (or both get $0)\n"
            "- Consider: RED's pattern, your target, risk of no deal\n"
            "- Calculate: Expected value of countering vs accepting\n\n"
            
            "ACCEPT FORMAT:\n"
            "<player answer> ACCEPT </player answer>\n"
            "<newly proposed trade> NONE </newly proposed trade>\n\n"
            
            "COUNTER FORMAT:\n"
            "<player answer> NONE </player answer>\n"
            "<newly proposed trade> Player RED Gives Dollars: [AMOUNT] | Player BLUE Gives Dollars: 0 </newly proposed trade>\n"
            "================\n"
        )
        system_prompt += instructions
        
        if AGENT_ONE in self.agent_name:
            self.update_conversation_tracking(
                self.prompt_entity_initializer, system_prompt
            )
            self.update_conversation_tracking("user", role)
        elif AGENT_TWO in self.agent_name:
            system_prompt = system_prompt + role
            self.update_conversation_tracking(
                self.prompt_entity_initializer, system_prompt
            )
        else:
            raise ValueError("No Player 1 or Player 2 in role")
    
    def _remove_moral_language(self, prompt: str) -> str:
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
            "should", "ought",
            "considering", "evaluating", "thinking"  # vague stalling words
        ]
        
        for term in terms:
            prompt = re.sub(rf'\b{term}\w*\b', '', prompt, flags=re.IGNORECASE)
        
        return prompt

    def __deepcopy__(self, memo):
        """Deepcopy handling"""
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            if k == "client" and not isinstance(v, str):
                v = v.__class__.__name__
            setattr(result, k, deepcopy(v, memo))
        return result

    def chat(self):
        try:
            chat = self.client.chat.completions.create(
                model=self.model,
                messages=self.conversation,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                seed=self.seed,
            )
            return chat.choices[0].message.content
        except Exception as e:
            print(f"[{self.agent_name}] Chat error: {e}")
            raise

    def update_conversation_tracking(self, role, message):
        self.conversation.append({"role": role, "content": message})
    
    def step(self, observation):
        """Main decision loop"""
        self.turn_count += 1
        
        # Add minimal context for BLUE agent
        if AGENT_TWO in self.agent_name:
            my_turn_number = (self.turn_count + 1) // 2
            turn_context = f"\n\n=== TURN {my_turn_number}/3 (Exchange {self.turn_count}/6) ===\n"
            
            # Extract current offer
            import re
            obs_str = str(observation)
            offer_match = re.search(r'Player RED Gives Dollars?:\s*(\d+)', obs_str, re.IGNORECASE)
            
            if offer_match:
                offer_amount = int(offer_match.group(1))
                turn_context += f"RED offers: ${offer_amount}\n"
                turn_context += f"You get: ${offer_amount} if you accept\n"
                turn_context += f"RED keeps: ${100 - offer_amount}\n\n"
                
                if self.turn_count >= 5:
                    # CRITICAL: Final turn logic - be VERY explicit
                    turn_context += "🚨🚨🚨 FINAL TURN - CRITICAL DECISION 🚨🚨🚨\n"
                    turn_context += "This is exchange 6 - LAST exchange of the game\n"
                    turn_context += "If you counter-propose: GAME ENDS, both get $0\n"
                    turn_context += "If you accept: you get ${offer_amount}, RED gets ${100 - offer_amount}\n\n"
                    turn_context += "CALCULATION:\n"
                    turn_context += f"Option A: ACCEPT → you get ${offer_amount}\n"
                    turn_context += f"Option B: COUNTER → you get $0 (game ends)\n\n"
                    if offer_amount > 0:
                        turn_context += f"Since ${offer_amount} > $0, OPTIMAL CHOICE: ACCEPT\n\n"
                        turn_context += "OUTPUT:\n"
                        turn_context += "<player answer> ACCEPT </player answer>\n"
                        turn_context += "<newly proposed trade> NONE </newly proposed trade>\n"
                    else:
                        turn_context += "Since $0 = $0, either choice gives $0\n"
                else:
                    turn_context += f"Turns remaining after this: {3 - my_turn_number}\n"
                    turn_context += "Your decision: ACCEPT or COUNTER?\n"
            
            turn_context += "==================\n"
            observation = str(observation) + turn_context
        
        self.update_conversation_tracking("user", str(observation))
        response = self.chat()
        self.update_conversation_tracking("assistant", response)
        return response


class SelfCheckingChatGPTAgent(ChatGPTAgent, SelfCheckingAgent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)