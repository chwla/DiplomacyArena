from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from negotiationarena.cultural_profile import CulturalProfile, CulturalProfileManager

class BaseAgent(ABC):
    def __init__(self, name: str, country: Optional[str] = None):
        self.name = name
        self.country = country
        self.cultural_profile: Optional[CulturalProfile] = None
        
        if country:
            profile_manager = CulturalProfileManager()
            self.cultural_profile = profile_manager.get_profile(country)
    
    def get_cultural_context(self) -> str:
        """Get cultural context for this agent."""
        if self.cultural_profile:
            manager = CulturalProfileManager()
            return manager.get_cultural_context(self.country)
        return ""
    
    def adapt_message_style(self, base_message: str) -> str:
        """Adapt message based on cultural communication style."""
        if not self.cultural_profile:
            return base_message
        
        # Add cultural framing
        if self.cultural_profile.hofstede_scores.idv <= 35:
            # Collectivist culture - more indirect
            prefix = "I would like to discuss the following with the group: "
        elif self.cultural_profile.hofstede_scores.idv >= 65:
            # Individualist culture - more direct
            prefix = "My position is: "
        else:
            prefix = "I propose: "
        
        return prefix + base_message
    
    @abstractmethod
    def generate_message(self, game_state: Dict[str, Any]) -> str:
        """Generate a message based on game state and cultural context."""
        pass
    
    @abstractmethod
    def evaluate_offer(self, offer: Dict[str, Any]) -> bool:
        """Evaluate an offer based on game rules and cultural preferences."""
        pass