"""
Abstract interface for memory storage
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from .schemas import NegotiationMemory, NegotiationTurn


class MemoryStore(ABC):
    """Abstract interface for memory storage backends"""
    
    @abstractmethod
    def store(self, memory: NegotiationMemory) -> str:
        """
        Store a memory in the database
        
        Args:
            memory: NegotiationMemory object to store
            
        Returns:
            memory_id: Unique identifier for the stored memory
        """
        pass
    
    @abstractmethod
    def store_batch(self, memories: List[NegotiationMemory]) -> List[str]:
        """
        Store multiple memories efficiently
        
        Args:
            memories: List of NegotiationMemory objects
            
        Returns:
            List of memory_ids
        """
        pass
    
    @abstractmethod
    def retrieve_by_similarity(
        self, 
        query_embedding: List[float], 
        k: int = 5,
        filters: Optional[Dict] = None
    ) -> List[NegotiationMemory]:
        """
        Retrieve memories by semantic similarity
        
        Args:
            query_embedding: Query vector
            k: Number of results to return
            filters: Optional filters (e.g., {"session_id": "xyz"})
            
        Returns:
            List of NegotiationMemory objects, ordered by relevance
        """
        pass
    
    @abstractmethod
    def retrieve_by_session(
        self, 
        session_id: str, 
        limit: Optional[int] = None
    ) -> List[NegotiationMemory]:
        """
        Get all memories from a specific session
        
        Args:
            session_id: Session identifier
            limit: Optional limit on number of results
            
        Returns:
            List of NegotiationMemory objects, ordered by turn_id
        """
        pass
    
    @abstractmethod
    def retrieve_recent(
        self, 
        n: int, 
        session_id: Optional[str] = None
    ) -> List[NegotiationMemory]:
        """
        Get the n most recent memories
        
        Args:
            n: Number of memories to retrieve
            session_id: Optional session filter
            
        Returns:
            List of NegotiationMemory objects, newest first
        """
        pass
    
    @abstractmethod
    def retrieve_by_type(
        self,
        message_type: str,
        session_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[NegotiationMemory]:
        """
        Retrieve memories by message type (offer, acceptance, etc.)
        
        Args:
            message_type: Type of message to filter
            session_id: Optional session filter
            limit: Optional limit on results
            
        Returns:
            List of NegotiationMemory objects
        """
        pass
    
    @abstractmethod
    def update(self, memory_id: str, updates: Dict) -> bool:
        """
        Update a memory's metadata
        
        Args:
            memory_id: ID of memory to update
            updates: Dictionary of fields to update
            
        Returns:
            Success boolean
        """
        pass
    
    @abstractmethod
    def delete(self, memory_id: str) -> bool:
        """Delete a specific memory"""
        pass
    
    @abstractmethod
    def delete_session(self, session_id: str) -> int:
        """
        Delete all memories from a session
        
        Returns:
            Number of memories deleted
        """
        pass
    
    @abstractmethod
    def get_stats(self, session_id: Optional[str] = None) -> Dict:
        """
        Get statistics about stored memories
        
        Returns:
            Dictionary with stats like total count, sessions, etc.
        """
        pass
    
    @abstractmethod
    def clear_all(self) -> int:
        """
        Clear all memories (use with caution!)
        
        Returns:
            Number of memories deleted
        """
        pass