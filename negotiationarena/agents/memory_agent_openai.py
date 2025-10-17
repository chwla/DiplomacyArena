"""
Memory agent with OpenAI embeddings - NO PICKLE ISSUES
OpenAI API calls can be pickled since they're just HTTP requests
"""
import os
import sys
from pathlib import Path
from typing import Optional, Dict

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from .chatgpt import ChatGPTAgent
except ImportError:
    from negotiationarena.agents.chatgpt import ChatGPTAgent


class MemoryAugmentedAgentOpenAI(ChatGPTAgent):
    """
    Memory agent using OpenAI embeddings - fully pickle-safe
    """
    
    def __init__(
        self,
        agent_name: str,
        model: str = "gpt-4",
        memory_config: Optional[Dict] = None,
        **kwargs
    ):
        super().__init__(agent_name=agent_name, model=model, **kwargs)
        
        # Configuration
        self._memory_config = memory_config or {}
        self._persist_dir = self._memory_config.get("persist_directory", "./memory_db")
        self._collection_name = self._memory_config.get("collection_name", f"agent_{agent_name}")
        
        self.retrieval_config = {
            "strategy": self._memory_config.get("strategy", "hybrid"),
            "k": self._memory_config.get("k", 5),
            "recency_weight": self._memory_config.get("recency_weight", 0.3),
            "similarity_weight": self._memory_config.get("similarity_weight", 0.7)
        }
        
        self.current_session_id = None
        self.turn_counter = 0
        self.memory_enabled = self._memory_config.get("enabled", True)
        
        # Memory components - None initially
        self._memory_store = None
        self._embedder = None
        self._retriever = None
        self._memory_ready = False
    
    def _init_memory(self):
        """Initialize with OpenAI embeddings - pickle-safe!"""
        if self._memory_ready or not self.memory_enabled:
            return
        
        try:
            from memory_system.core.vector_store import ChromaMemoryStore
            from memory_system.core.retriever import MemoryRetriever
            from memory_system.utils.embeddings import create_embedder
            
            # Use OpenAI embeddings - these ARE picklable!
            self._embedder = create_embedder(
                embedder_type="openai",
                model="text-embedding-3-small"
            )
            
            self._memory_store = ChromaMemoryStore(
                persist_directory=self._persist_dir,
                collection_name=self._collection_name
            )
            
            self._retriever = MemoryRetriever(self._memory_store, self._embedder)
            self._memory_ready = True
            
            print(f"[{self.agent_name}] Memory ready with OpenAI embeddings")
            
        except Exception as e:
            print(f"[{self.agent_name}] Memory init failed: {e}")
            self.memory_enabled = False
    
    def __getstate__(self):
        """Pickle handling - OpenAI embedder IS picklable"""
        state = self.__dict__.copy()
        # Only remove ChromaDB store (has locks)
        # OpenAI embedder can stay!
        state['_memory_store'] = None
        state['_retriever'] = None
        state['_memory_ready'] = False
        if 'client' in state:
            state['client'] = None
        return state
    
    def __setstate__(self, state):
        """Restore after unpickling"""
        self.__dict__.update(state)
    
    def init_agent(self, game_prompt: str, role: str = ""):
        """Initialize agent"""
        super().init_agent(game_prompt, role)
        
        if not self.current_session_id:
            import uuid
            self.current_session_id = f"game_{uuid.uuid4().hex[:8]}"
    
    def step(self, observation):
        """Main game method - inject memory here"""
        # Ensure OpenAI client exists
        if not hasattr(self, 'client') or self.client is None:
            from openai import OpenAI
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Initialize memory
        if self.memory_enabled and not self._memory_ready:
            self._init_memory()
        
        # Retrieve relevant memories
        if self.memory_enabled and self._memory_ready and self.turn_counter > 0:
            try:
                obs_str = str(observation)[-200:] if observation else ""
                relevant = self._retriever.retrieve_relevant(
                    query=obs_str,
                    session_id=self.current_session_id,
                    **self.retrieval_config
                )
                
                if relevant.memories:
                    # Inject memory into observation
                    memory_context = "\n\n[RELEVANT PAST CONTEXT]:\n"
                    for mem in relevant.memories[:3]:
                        memory_context += f"- Turn {mem.turn.turn_id}: {mem.turn.message[:100]}\n"
                    
                    # Modify observation to include memory
                    if isinstance(observation, str):
                        observation = observation + memory_context
                    
            except Exception as e:
                print(f"[{self.agent_name}] Retrieval error: {e}")
        
        # Get response
        response = super().step(observation)
        
        # Store turn
        if self.memory_enabled and self._memory_ready:
            try:
                self._store_turn(observation, response)
            except Exception as e:
                print(f"[{self.agent_name}] Store error: {e}")
        
        self.turn_counter += 1
        return response
    
    def _store_turn(self, observation, response):
        """Store turn in memory"""
        from datetime import datetime
        from memory_system.core.schemas import NegotiationTurn, NegotiationMemory
        
        # Store observation
        obs_str = str(observation)[-400:] if observation else ""
        
        obs_turn = NegotiationTurn(
            turn_id=self.turn_counter * 2,
            session_id=self.current_session_id,
            timestamp=datetime.now(),
            speaker="environment",
            message=obs_str,
            message_type="observation",
            game_type="negotiation",
            role="environment"
        )
        
        obs_embedding = self._embedder.generate(obs_str)
        obs_memory = NegotiationMemory(
            memory_id=None,
            turn=obs_turn,
            embedding=obs_embedding,
            game_state={}
        )
        self._memory_store.store(obs_memory)
        
        # Store response
        resp_str = str(response)[:400] if response else ""
        
        resp_turn = NegotiationTurn(
            turn_id=self.turn_counter * 2 + 1,
            session_id=self.current_session_id,
            timestamp=datetime.now(),
            speaker=self.agent_name,
            message=resp_str,
            message_type=self._classify(resp_str),
            game_type="negotiation",
            role=self.agent_name
        )
        
        resp_embedding = self._embedder.generate(resp_str)
        resp_memory = NegotiationMemory(
            memory_id=None,
            turn=resp_turn,
            embedding=resp_embedding,
            game_state={},
            importance_score=self._importance(resp_str),
            is_critical=self._critical(resp_str)
        )
        self._memory_store.store(resp_memory)
    
    def _classify(self, msg: str) -> str:
        m = msg.lower()
        if "accept" in m: return "acceptance"
        if "reject" in m: return "rejection"
        if "propose" in m or "offer" in m: return "offer"
        if "counter" in m: return "counteroffer"
        return "chat"
    
    def _importance(self, msg: str) -> float:
        keywords = ["deal", "offer", "accept", "reject", "final"]
        matches = sum(1 for k in keywords if k in msg.lower())
        return min(0.5 + matches * 0.1, 1.0)
    
    def _critical(self, msg: str) -> bool:
        return any(w in msg.lower() for w in ["deal", "accept", "reject", "final"])
    
    def get_memory_stats(self) -> Dict:
        if not self.memory_enabled:
            return {"memory_enabled": False}
        
        self._init_memory()
        
        if self._memory_ready and self._memory_store:
            return self._memory_store.get_stats(session_id=self.current_session_id)
        
        return {"memory_enabled": True, "ready": self._memory_ready}