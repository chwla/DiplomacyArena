import json
import os
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass

@dataclass
class HofstedeScores:
    pdi: int  # Power Distance Index
    idv: int  # Individualism vs Collectivism
    mas: int  # Masculinity vs Femininity
    uai: int  # Uncertainty Avoidance Index
    ltowvs: float  # Long-term Orientation
    ivr: float  # Indulgence vs Restraint

@dataclass
class InteractionProfile:
    type: str
    behaviour_rules: str

@dataclass
class CulturalProfile:
    country: str
    country_code: str
    hofstede_scores: HofstedeScores
    interaction_profile: InteractionProfile
    
    def get_negotiation_style(self) -> str:
        """Generate a description of negotiation style based on cultural dimensions."""
        styles = []
        
        # Individualism dimension
        if self.hofstede_scores.idv <= 35:
            styles.append("group-oriented decision making")
        elif self.hofstede_scores.idv >= 65:
            styles.append("independent decision making")
        
        # Power Distance dimension
        if self.hofstede_scores.pdi <= 35:
            styles.append("egalitarian approach")
        elif self.hofstede_scores.pdi >= 65:
            styles.append("hierarchical respect")
        
        # Uncertainty Avoidance dimension
        if self.hofstede_scores.uai <= 35:
            styles.append("flexible and adaptive")
        elif self.hofstede_scores.uai >= 65:
            styles.append("structured and risk-averse")
        
        return ", ".join(styles) if styles else "balanced approach"
    
    def get_communication_style(self) -> str:
        """Generate communication style description."""
        if self.hofstede_scores.idv <= 35:
            return "indirect and context-aware communication"
        elif self.hofstede_scores.idv >= 65:
            return "direct and explicit communication"
        return "moderate directness in communication"

class CulturalProfileManager:
    def __init__(self, profiles_dir: str = "profiles"):
        self.profiles_dir = Path(profiles_dir)
        self.profiles: Dict[str, CulturalProfile] = {}
        self._load_profiles()
    
    def _load_profiles(self):
        """Load all cultural profiles from JSON files."""
        if not self.profiles_dir.exists():
            return
        
        for profile_file in self.profiles_dir.glob("*_profile.json"):
            try:
                with open(profile_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    profile = self._parse_profile(data)
                    self.profiles[profile.country.lower()] = profile
            except Exception as e:
                print(f"Warning: Could not load profile {profile_file}: {e}")
    
    def _parse_profile(self, data: Dict) -> CulturalProfile:
        """Parse JSON data into CulturalProfile object."""
        hofstede = HofstedeScores(
            pdi=data['hofstede_scores']['pdi'],
            idv=data['hofstede_scores']['idv'],
            mas=data['hofstede_scores']['mas'],
            uai=data['hofstede_scores']['uai'],
            ltowvs=data['hofstede_scores']['ltowvs'],
            ivr=data['hofstede_scores']['ivr']
        )
        
        interaction = InteractionProfile(
            type=data['interaction_profile']['type'],
            behaviour_rules=data['interaction_profile']['behaviour_rules']
        )
        
        return CulturalProfile(
            country=data['metadata']['country'],
            country_code=data['metadata']['country_code'],
            hofstede_scores=hofstede,
            interaction_profile=interaction
        )
    
    def get_profile(self, country: str) -> Optional[CulturalProfile]:
        """Retrieve cultural profile for a specific country."""
        return self.profiles.get(country.lower())
    
    def list_available_countries(self) -> List[str]:
        """Return list of available country profiles."""
        return list(self.profiles.keys())
    
    def get_cultural_context(self, country: str) -> str:
        """Generate a comprehensive cultural context string for prompts."""
        profile = self.get_profile(country)
        if not profile:
            return ""
        
        context_parts = [
            f"You are negotiating as a representative from {profile.country}.",
            f"Cultural background: {profile.interaction_profile.type}",
            f"Behavior guidelines: {profile.interaction_profile.behaviour_rules}",
            f"Negotiation style: {profile.get_negotiation_style()}",
            f"Communication approach: {profile.get_communication_style()}"
        ]
        
        return "\n".join(context_parts)