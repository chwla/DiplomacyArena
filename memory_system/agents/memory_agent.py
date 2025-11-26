"""
Memory-augmented negotiation agent with OpenAI and Gemini backends
"""
from typing import List, Dict, Optional
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from ..core.memory_store import MemoryStore
from ..core.retriever import MemoryRetriever
from ..core.schemas import NegotiationTurn, NegotiationMemory
from ..utils.embeddings import EmbeddingGenerator


class MemoryAugmentedNegotiator:
    """
    Standalone memory-augmented negotiation agent using OpenAI or Gemini
    """
    
    def __init__(
        self,
        agent_name: str,
        llm_backend: str = "llama",  # Changed default to llama
        model: str = None,
        memory_store: MemoryStore = None,
        retriever: MemoryRetriever = None,
        embedding_generator: EmbeddingGenerator = None,
        retrieval_config: Dict = None,
        api_key: str = None
    ):
        """
        Initialize memory-augmented negotiator
        
        Args:
            agent_name: Name of this agent
            llm_backend: "openai", "gemini", or "llama" (default: "llama")
            model: Model name
            memory_store: Storage backend
            retriever: Retrieval system
            embedding_generator: Embedder
            retrieval_config: Retrieval strategy configuration
            api_key: API key for LLM backend
        """
        self.agent_name = agent_name
        self.llm_backend = llm_backend
        
        self.memory_store = memory_store
        self.retriever = retriever
        self.embedder = embedding_generator
        
        self.retrieval_config = retrieval_config or {
            "strategy": "hybrid",
            "k": 5,
            "recency_weight": 0.3,
            "similarity_weight": 0.7
        }
        
        self.current_session_id = None
        self.turn_counter = 0
        
        if llm_backend == "openai":
            self._init_openai(model, api_key)
        elif llm_backend == "gemini":
            self._init_gemini(model, api_key)
        elif llm_backend == "llama":
            self._init_llama(model, api_key)
        else:
            self.llm_client = None
            self.model = model
    
    def _init_openai(self, model: str = None, api_key: str = None):
        """Initialize OpenAI backend"""
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "openai not installed. "
                "Install with: pip install openai"
            )
        
        api_key = api_key or os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment or .env file")
        
        self.model = model or "gpt-4"
        self.llm_client = OpenAI(api_key=api_key)
        
        print(f"[MemoryAgent] Initialized with OpenAI model: {self.model}")
    
    def _init_gemini(self, model: str = None, api_key: str = None):
        """Initialize Gemini backend"""
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError(
                "google-generativeai not installed. "
                "Install with: pip install google-generativeai"
            )
        
        # Try both GEMINI_API_KEY and GOOGLE_API_KEY (reads from .env via load_dotenv)
        api_key = api_key or os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
        if not api_key:
            raise ValueError(
                "API key not found. Set GEMINI_API_KEY or GOOGLE_API_KEY in .env file"
            )
        
        genai.configure(api_key=api_key)
        # Use the stable Gemini 1.5 Flash model
        self.model = model or "gemini-1.5-flash-latest"
        self.llm_client = genai.GenerativeModel(
            self.model,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
            )
        )
        
        print(f"[MemoryAgent] Initialized with Gemini model: {self.model}")
    
    def _init_llama(self, model: str = None, api_key: str = None):
        """Initialize DeepSeek R1 via OpenRouter (FREE with rate limiting)"""
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "openai not installed. "
                "Install with: pip install openai"
            )
        
        self.model = model or "deepseek/deepseek-r1-distill-llama-70b:free"
        
        # Use OpenRouter API - FREE with rate limiting
        openrouter_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not openrouter_key:
            raise ValueError("OPENROUTER_API_KEY not found in .env file")
        
        self.llm_client = OpenAI(
            api_key=openrouter_key,
            base_url="https://openrouter.ai/api/v1"
        )
        
        print(f"[MemoryAgent] Initialized with OpenRouter model: {self.model}")
    
    def start_session(self, session_id: str):
        """Initialize a new negotiation session"""
        self.current_session_id = session_id
        self.turn_counter = 0
        print(f"[MemoryAgent] Started session: {session_id}")
    
    def generate_response(
        self,
        message: str,
        game_context: Dict,
        system_prompt: str,
        role: str = "unknown"
    ) -> str:
        """
        Generate response with memory augmentation
        
        Args:
            message: Current message from opponent
            game_context: Current game state
            system_prompt: System instructions for agent
            role: Agent's role in negotiation
            
        Returns:
            Generated response
        """
        relevant_memories = self.retriever.retrieve_relevant(
            query=message,
            session_id=self.current_session_id,
            **self.retrieval_config
        )
        
        augmented_prompt = self._build_memory_augmented_prompt(
            current_message=message,
            memories=relevant_memories.memories,
            game_context=game_context,
            system_prompt=system_prompt
        )
        
        response = self._call_llm(augmented_prompt)
        
        self._store_interaction(
            message=message,
            response=response,
            game_context=game_context,
            role=role
        )
        
        self.turn_counter += 1
        return response
    
    def _build_memory_augmented_prompt(
        self,
        current_message: str,
        memories: List[NegotiationMemory],
        game_context: Dict,
        system_prompt: str
    ) -> str:
        """Build prompt with retrieved memories"""
        
        prompt_parts = [system_prompt, "\n\n"]
        
        if memories:
            prompt_parts.append("## Relevant Past Interactions:\n")
            for i, mem in enumerate(memories[:5], 1):
                prompt_parts.append(
                    f"{i}. [Turn {mem.turn.turn_id}] {mem.turn.speaker}: "
                    f"{mem.turn.message}\n"
                )
                if mem.turn.offer_details:
                    prompt_parts.append(f"   Offer Details: {mem.turn.offer_details}\n")
            prompt_parts.append("\n")
        
        if game_context:
            prompt_parts.append("## Current Game State:\n")
            for key, value in game_context.items():
                prompt_parts.append(f"- {key}: {value}\n")
            prompt_parts.append("\n")
        
        prompt_parts.append(f"## Current Message:\n{current_message}\n\n")
        prompt_parts.append("Your response:")
        
        return "".join(prompt_parts)
    
    def _call_llm(self, prompt: str) -> str:
        """Call LLM with prompt"""
        if self.llm_backend == "openai":
            response = self.llm_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            return response.choices[0].message.content
        
        elif self.llm_backend == "gemini":
            try:
                response = self.llm_client.generate_content(prompt)
                return response.text
            except Exception as e:
                # Handle potential Gemini API errors
                print(f"[MemoryAgent] Gemini API error: {e}")
                raise
        
        elif self.llm_backend == "llama":
            try:
                response = self.llm_client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7
                )
                return response.choices[0].message.content
            except Exception as e:
                # Handle potential Together AI API errors
                print(f"[MemoryAgent] Llama API error: {e}")
                raise
        
        else:
            raise ValueError(f"Unsupported LLM backend: {self.llm_backend}")
    
    def _store_interaction(
        self,
        message: str,
        response: str,
        game_context: Dict,
        role: str
    ):
        """Store the current interaction in memory"""
        opponent_turn = NegotiationTurn(
            turn_id=self.turn_counter * 2,
            session_id=self.current_session_id,
            timestamp=datetime.now(),
            speaker="opponent",
            message=message,
            message_type=self._classify_message(message),
            game_type=game_context.get("game_type", "unknown"),
            role="opponent"
        )
        
        embedding = self.embedder.generate(message)
        opponent_memory = NegotiationMemory(
            memory_id=None,
            turn=opponent_turn,
            embedding=embedding,
            game_state=game_context
        )
        self.memory_store.store(opponent_memory)
        
        self_turn = NegotiationTurn(
            turn_id=self.turn_counter * 2 + 1,
            session_id=self.current_session_id,
            timestamp=datetime.now(),
            speaker=self.agent_name,
            message=response,
            message_type=self._classify_message(response),
            game_type=game_context.get("game_type", "unknown"),
            role=role
        )
        
        self_embedding = self.embedder.generate(response)
        self_memory = NegotiationMemory(
            memory_id=None,
            turn=self_turn,
            embedding=self_embedding,
            game_state=game_context,
            importance_score=self._calculate_importance(response),
            is_critical=self._is_critical_message(response)
        )
        self.memory_store.store(self_memory)
    
    def _classify_message(self, message: str) -> str:
        """Classify message type for diplomacy context"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["accept", "deal", "agree", "yes"]):
            return "acceptance"
        elif any(word in message_lower for word in ["reject", "no thanks", "refuse", "decline"]):
            return "rejection"
        elif any(word in message_lower for word in ["alliance", "ally", "together", "cooperate"]):
            return "alliance"
        elif any(word in message_lower for word in ["betray", "attack you", "break"]):
            return "betrayal"
        elif any(word in message_lower for word in ["offer", "propose", "suggest", "how about"]):
            return "offer"
        elif any(word in message_lower for word in ["counter", "instead"]):
            return "counteroffer"
        else:
            return "chat"
    
    def _calculate_importance(self, message: str) -> float:
        """Calculate importance score for message"""
        importance_keywords = [
            "alliance", "betray", "attack", "defend", "promise", 
            "guarantee", "deal", "treaty", "agree", "support"
        ]
        
        message_lower = message.lower()
        matches = sum(1 for keyword in importance_keywords if keyword in message_lower)
        
        base_score = 0.5
        keyword_boost = min(matches * 0.1, 0.4)
        
        return min(base_score + keyword_boost, 1.0)
    
    def _is_critical_message(self, message: str) -> bool:
        """Determine if message is critical"""
        critical_keywords = [
            "alliance", "betray", "treaty", "deal", "promise to",
            "guarantee", "commit to", "declare war"
        ]
        
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in critical_keywords)
    
    def get_memory_stats(self) -> Dict:
        """Get statistics about stored memories"""
        stats = self.memory_store.get_stats(session_id=self.current_session_id)
        stats["current_turn"] = self.turn_counter
        return stats
    
    def get_negotiation_history(self, limit: int = None) -> List[NegotiationMemory]:
        """Get full negotiation history for current session"""
        return self.memory_store.retrieve_by_session(
            session_id=self.current_session_id,
            limit=limit
        )
    
    def analyze_opponent_pattern(self) -> Dict:
        """Analyze opponent's negotiation patterns"""
        return self.retriever.analyze_concession_pattern(
            session_id=self.current_session_id,
            speaker="opponent"
        )