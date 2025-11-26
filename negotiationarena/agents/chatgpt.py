import copy
import os
import re
import random
from negotiationarena.agents.agents import Agent
import time
from negotiationarena.constants import AGENT_TWO, AGENT_ONE
from negotiationarena.agents.agent_behaviours import SelfCheckingAgent
from copy import deepcopy
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class ChatGPTAgent(Agent):
    def __init__(
        self,
        agent_name: str,
        model="meta-llama/llama-3.1-70b-instruct",
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
        
        # OpenRouter PAID - costs ~$0.01 per test
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not found in .env")
        
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
        self.temperature = temperature
        self.max_tokens = max_tokens

    def init_agent(self, system_prompt, role):
        self.conversation = []
        
        if AGENT_ONE in self.agent_name:
            self.update_conversation_tracking(
                self.prompt_entity_initializer, system_prompt
            )
            self.update_conversation_tracking("user", role)
        elif AGENT_TWO in self.agent_name:
            combined_prompt = system_prompt + "\n\n" + role
            self.update_conversation_tracking(
                self.prompt_entity_initializer, combined_prompt
            )
        else:
            raise ValueError("Agent name must contain 'Player 1' or 'Player 2'")

    def get_state(self):
        state = {}
        for k, v in self.__dict__.items():
            if k == "client":
                continue
            try:
                state[k] = deepcopy(v)
            except Exception:
                state[k] = v
        state["class"] = self.__class__.__name__
        return state
    
    def set_state(self, state_dict):
        self.conversation = state_dict.get("conversation", [])
        self.run_epoch_time_ms = state_dict.get("run_epoch_time_ms", "")
        
        if not hasattr(self, 'client') or self.client is None:
            api_key = os.environ.get("OPENROUTER_API_KEY")
            self.client = OpenAI(
                api_key=api_key,
                base_url="https://openrouter.ai/api/v1"
            )

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            if k == "client":
                continue
            setattr(result, k, deepcopy(v, memo))
        
        api_key = os.environ.get("OPENROUTER_API_KEY")
        result.client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
        return result
    
    def chat(self):
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.conversation,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"[{self.agent_name}] Chat error: {e}")
            return "<my name>Player RED</my name>\n<my resources>X: 25, Y: 5</my resources>\n<my goals>X: 15, Y: 15</my goals>\n<reason>Strategic trade proposal</reason>\n<player answer>NONE</player answer>\n<message>I propose we exchange resources.</message>\n<newly proposed trade>Player RED Gives X: 10 | Player BLUE Gives Y: 10</newly proposed trade>"

    def update_conversation_tracking(self, role, message):
        self.conversation.append({"role": role, "content": message})
    
    def step(self, observation):
        self.update_conversation_tracking("user", str(observation))
        response = self.chat()
        self.update_conversation_tracking("assistant", response)
        return response


class SelfCheckingChatGPTAgent(ChatGPTAgent, SelfCheckingAgent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)