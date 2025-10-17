"""
Memory retrieval with multiple strategies - FIXED VERSION
"""
from typing import List, Dict, Optional
from .memory_store import MemoryStore
from .schemas import NegotiationMemory, RetrievalResult
from ..utils.embeddings import EmbeddingGenerator


class MemoryRetriever:
    """
    Handles memory retrieval with different strategies
    """
    
    def __init__(
        self, 
        memory_store: MemoryStore,
        embedding_generator: EmbeddingGenerator
    ):
        """
        Initialize retriever
        
        Args:
            memory_store: Storage backend
            embedding_generator: Embedding generator for queries
        """
        self.store = memory_store
        self.embedder = embedding_generator
    
    def retrieve_relevant(
        self,
        query: str,
        session_id: str,
        strategy: str = "hybrid",
        k: int = 5,
        recency_weight: float = 0.3,
        similarity_weight: float = 0.7,
        **kwargs
    ) -> RetrievalResult:
        """
        Retrieve relevant memories using specified strategy
        
        Args:
            query: Query text
            session_id: Session to search within
            strategy: "semantic", "recency", "hybrid", "critical"
            k: Number of memories to retrieve
            recency_weight: Weight for recency in hybrid mode
            similarity_weight: Weight for similarity in hybrid mode
            
        Returns:
            RetrievalResult with memories and metadata
        """
        if strategy == "semantic":
            memories = self._semantic_retrieval(query, session_id, k)
        elif strategy == "recency":
            memories = self._recency_retrieval(session_id, k)
        elif strategy == "hybrid":
            memories = self._hybrid_retrieval(
                query, session_id, k, recency_weight, similarity_weight
            )
        elif strategy == "critical":
            memories = self._critical_retrieval(session_id, k)
        else:
            raise ValueError(f"Unknown retrieval strategy: {strategy}")
        
        return RetrievalResult(
            memories=memories,
            query=query,
            strategy=strategy
        )
    
    def _semantic_retrieval(
        self, 
        query: str, 
        session_id: str, 
        k: int
    ) -> List[NegotiationMemory]:
        """Pure semantic similarity search"""
        query_embedding = self.embedder.generate(query)
        
        memories = self.store.retrieve_by_similarity(
            query_embedding=query_embedding,
            k=k,
            filters={"session_id": session_id}
        )
        
        return memories
    
    def _recency_retrieval(
        self, 
        session_id: str, 
        k: int
    ) -> List[NegotiationMemory]:
        """Retrieve most recent memories"""
        return self.store.retrieve_recent(n=k, session_id=session_id)
    
    def _hybrid_retrieval(
        self,
        query: str,
        session_id: str,
        k: int,
        recency_weight: float,
        similarity_weight: float
    ) -> List[NegotiationMemory]:
        """
        Combine semantic similarity with recency
        
        Algorithm:
        1. Get top 2*k results from semantic search
        2. Get top 2*k most recent memories
        3. Merge and score using weighted combination
        4. Return top k
        """
        all_memories = self.store.retrieve_by_session(session_id)
        
        if not all_memories:
            return []
        
        candidate_k = min(k * 3, 50)
        
        semantic_results = self._semantic_retrieval(query, session_id, k=candidate_k)
        recent_results = self._recency_retrieval(session_id, k=candidate_k)
        
        if not semantic_results and not recent_results:
            return []
        
        all_candidates = {}
        for mem in semantic_results + recent_results:
            if mem.memory_id not in all_candidates:
                all_candidates[mem.memory_id] = mem
        
        if not all_candidates:
            return []
        
        scored_memories = []
        
        max_turn = max(m.turn.turn_id for m in all_candidates.values())
        max_turn = max(max_turn, 1)
        
        for mem in all_candidates.values():
            recency_score = mem.turn.turn_id / max_turn
            
            semantic_rank = next(
                (i for i, m in enumerate(semantic_results) if m.memory_id == mem.memory_id),
                len(semantic_results)
            )
            semantic_score = 1 - (semantic_rank / max(len(semantic_results), 1))
            
            importance_boost = mem.importance_score * 0.1
            critical_boost = 0.1 if mem.is_critical else 0.0
            
            combined_score = (
                recency_weight * recency_score +
                similarity_weight * semantic_score +
                importance_boost +
                critical_boost
            )
            
            scored_memories.append((combined_score, mem))
        
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        return [mem for _, mem in scored_memories[:k]]
    
    def _critical_retrieval(
        self, 
        session_id: str, 
        k: int
    ) -> List[NegotiationMemory]:
        """Retrieve critical moments (offers, deals, deadlocks)"""
        all_memories = self.store.retrieve_by_session(session_id)
        
        if not all_memories:
            return []
        
        critical = [m for m in all_memories if m.is_critical]
        
        if len(critical) < k:
            important = [
                m for m in all_memories 
                if not m.is_critical and m.importance_score > 0.7
            ]
            important.sort(key=lambda m: m.importance_score, reverse=True)
            critical.extend(important[:k - len(critical)])
        
        return critical[:k]
    
    def retrieve_offer_history(
        self, 
        session_id: str, 
        resource: Optional[str] = None
    ) -> List[NegotiationMemory]:
        """
        Retrieve all offers made during negotiation
        
        Args:
            session_id: Session ID
            resource: Optional filter for specific resource
            
        Returns:
            List of offer memories
        """
        offers = self.store.retrieve_by_type(
            message_type="offer",
            session_id=session_id
        )
        
        counteroffers = self.store.retrieve_by_type(
            message_type="counteroffer",
            session_id=session_id
        )
        
        all_offers = offers + counteroffers
        
        if resource:
            all_offers = [
                m for m in all_offers 
                if resource in m.turn.resources_mentioned
            ]
        
        all_offers.sort(key=lambda m: m.turn.turn_id)
        
        return all_offers
    
    def retrieve_conversation_phase(
        self,
        session_id: str,
        phase: str,
        k: int = 10
    ) -> List[NegotiationMemory]:
        """
        Retrieve memories from a specific negotiation phase
        
        Args:
            session_id: Session ID
            phase: "opening", "bargaining", "closing"
            k: Max memories to return
            
        Returns:
            Memories from that phase
        """
        all_memories = self.store.retrieve_by_session(session_id)
        
        if not all_memories:
            return []
        
        total_turns = max(m.turn.turn_id for m in all_memories)
        
        if phase == "opening":
            max_turn = int(total_turns * 0.2)
            phase_memories = [m for m in all_memories if m.turn.turn_id <= max_turn]
        
        elif phase == "bargaining":
            start_turn = int(total_turns * 0.2)
            end_turn = int(total_turns * 0.8)
            phase_memories = [
                m for m in all_memories 
                if start_turn < m.turn.turn_id <= end_turn
            ]
        
        elif phase == "closing":
            start_turn = int(total_turns * 0.8)
            phase_memories = [m for m in all_memories if m.turn.turn_id > start_turn]
        
        else:
            raise ValueError(f"Unknown phase: {phase}")
        
        return phase_memories[:k]
    
    def analyze_concession_pattern(
        self,
        session_id: str,
        speaker: Optional[str] = None
    ) -> Dict:
        """
        Analyze concession patterns in negotiation
        
        Returns:
            Dictionary with concession analysis
        """
        offers = self.retrieve_offer_history(session_id)
        
        if speaker:
            offers = [o for o in offers if o.turn.speaker == speaker]
        
        if not offers:
            return {"concessions": [], "pattern": "no_offers", "total_offers": 0}
        
        concessions = []
        for i in range(1, len(offers)):
            prev_offer = offers[i-1]
            curr_offer = offers[i]
            
            if prev_offer.turn.offer_details and curr_offer.turn.offer_details:
                concessions.append({
                    "turn": curr_offer.turn.turn_id,
                    "from": prev_offer.turn.offer_details,
                    "to": curr_offer.turn.offer_details
                })
        
        return {
            "total_offers": len(offers),
            "concessions": concessions,
            "pattern": "cooperative" if len(concessions) > 0 else "rigid"
        }