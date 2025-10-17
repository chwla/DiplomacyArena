from typing import Optional
from negotiationarena.cultural_profile import CulturalProfileManager

class CulturalPromptBuilder:
    def __init__(self):
        self.profile_manager = CulturalProfileManager()
    
    def build_system_prompt(self, country: Optional[str] = None, 
                           base_role: str = "negotiator") -> str:
        """Build a culturally-aware system prompt."""
        base_prompt = f"You are a professional {base_role} in a negotiation scenario."
        
        if not country:
            return base_prompt
        
        cultural_context = self.profile_manager.get_cultural_context(country)
        if not cultural_context:
            return base_prompt
        
        return f"{base_prompt}\n\n{cultural_context}\n\nRemember to maintain these cultural characteristics throughout the negotiation."
    
    def build_negotiation_prompt(self, country: Optional[str], 
                                 game_context: str,
                                 current_state: str) -> str:
        """Build a complete negotiation prompt with cultural awareness."""
        parts = [
            "Current Negotiation Context:",
            game_context,
            "",
            "Current State:",
            current_state,
            ""
        ]
        
        if country:
            profile = self.profile_manager.get_profile(country)
            if profile:
                parts.extend([
                    "Your Cultural Framework:",
                    f"- Interaction Style: {profile.interaction_profile.type}",
                    f"- Negotiation Approach: {profile.get_negotiation_style()}",
                    f"- Communication Style: {profile.get_communication_style()}",
                    ""
                ])
        
        parts.append("What is your next move? Respond in character.")
        
        return "\n".join(parts)
    
    def get_reflection_prompt(self, country: Optional[str], 
                             negotiation_history: str) -> str:
        """Generate a prompt for reflecting on negotiation behavior."""
        base = "Reflect on the following negotiation:\n\n" + negotiation_history
        
        if country:
            profile = self.profile_manager.get_profile(country)
            if profile:
                base += f"\n\nDid your behavior align with {profile.country} cultural norms?"
                base += f"\nConsider: {profile.interaction_profile.behaviour_rules}"
        
        return base