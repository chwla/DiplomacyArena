"""
Stateless Agent - No memory between turns
Save as: negotiationarena/agents/stateless_agent.py
"""
import os
from openai import OpenAI
from negotiationarena.agents.chatgpt import ChatGPTAgent


class StatelessAgent(ChatGPTAgent):
    """
    Agent with NO memory between turns - each response is independent
    Perfect for baseline comparisons against memory-augmented agents
    """
    
    def __init__(self, agent_name: str, model: str = "gpt-4-1106-preview", **kwargs):
        super().__init__(agent_name=agent_name, model=model, **kwargs)
        self._base_prompt = None
    
    def init_agent(self, game_prompt: str, role: str = ""):
        """Store base prompt but don't accumulate history"""
        self._base_prompt = game_prompt
        self.conversation = []  # Keep empty - no history
    
    def step(self, observation):
        """
        Process observation with NO memory of previous turns
        Each decision is made independently based only on current observation
        """
        # Ensure OpenAI client exists
        if not hasattr(self, 'client') or self.client is None:
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Build fresh messages every time - NO HISTORY
        messages = [
            {"role": "system", "content": self._base_prompt},
            {"role": "user", "content": str(observation)}
        ]
        
        # Get response
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
        
        return response.choices[0].message.content
    
    def update_conversation_tracking(self, role: str, content: str):
        """Override to prevent memory accumulation"""
        pass  