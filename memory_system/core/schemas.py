"""
Memory system data schemas for negotiation agents
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import json


@dataclass
class NegotiationTurn:
    """Represents a single turn in a negotiation"""
    turn_id: int
    session_id: str
    timestamp: datetime
    speaker: str
    message: str
    message_type: str  # "offer", "counteroffer", "acceptance", "rejection", "chat"
    
    # Structured data extracted from message
    offer_details: Optional[Dict[str, Any]] = None
    resources_mentioned: Dict[str, float] = field(default_factory=dict)
    sentiment: Optional[str] = None
    
    # Metadata
    game_type: str = "unknown"
    role: str = "unknown"  # "buyer", "seller", etc.
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        return {
            "turn_id": self.turn_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "speaker": self.speaker,
            "message": self.message,
            "message_type": self.message_type,
            "offer_details": self.offer_details,
            "resources_mentioned": self.resources_mentioned,
            "sentiment": self.sentiment,
            "game_type": self.game_type,
            "role": self.role
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'NegotiationTurn':
        """Create from dictionary"""
        data = data.copy()
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class NegotiationMemory:
    """A memory entry for storage in the vector database"""
    memory_id: Optional[str]
    turn: NegotiationTurn
    embedding: List[float]
    
    # Context
    previous_turns: List[int] = field(default_factory=list)
    game_state: Dict[str, Any] = field(default_factory=dict)
    
    # Importance scoring
    importance_score: float = 0.5  # 0-1 scale
    is_critical: bool = False  # Major offer, deal, deadlock
    
    # Metadata for retrieval
    tags: List[str] = field(default_factory=list)
    
    def __repr__(self) -> str:
        return (f"NegotiationMemory(id={self.memory_id}, "
                f"turn={self.turn.turn_id}, "
                f"speaker={self.turn.speaker}, "
                f"type={self.turn.message_type})")


@dataclass
class ConversationSummary:
    """Summary of a conversation phase"""
    session_id: str
    phase: str  # "opening", "bargaining", "closing"
    turn_range: tuple  # (start_turn, end_turn)
    summary_text: str
    key_offers: List[Dict[str, Any]] = field(default_factory=list)
    concessions_made: List[Dict[str, Any]] = field(default_factory=list)
    opponent_preferences: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "session_id": self.session_id,
            "phase": self.phase,
            "turn_range": self.turn_range,
            "summary_text": self.summary_text,
            "key_offers": self.key_offers,
            "concessions_made": self.concessions_made,
            "opponent_preferences": self.opponent_preferences
        }


@dataclass
class RetrievalResult:
    """Result from memory retrieval"""
    memories: List[NegotiationMemory]
    query: str
    strategy: str
    relevance_scores: List[float] = field(default_factory=list)
    
    def __len__(self) -> int:
        return len(self.memories)
    
    def __iter__(self):
        return iter(self.memories)
    
    def __getitem__(self, idx):
        return self.memories[idx]