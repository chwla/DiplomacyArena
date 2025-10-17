import sys
sys.path.append(".")
from negotiationarena.alternating_game import AlternatingGame
from negotiationarena.constants import *


class SimpleGame(AlternatingGame):
    def __init__(
        self,
        resources_support_set,
        player_initial_resources,
        player_social_behaviour,
        player_roles,
        game_interface=None,
        **kwargs
    ):
        # Remove end_tag from kwargs if present to avoid parent class issues
        kwargs.pop('end_tag', None)
        
        super().__init__(**kwargs)
        
        self.game_state = [
            {
                "current_iteration": "START",
                "turn": "None",
                "settings": dict(
                    resources_support_set=resources_support_set,
                    player_initial_resources=player_initial_resources,
                    player_social_behaviour=player_social_behaviour,
                    player_roles=player_roles,
                ),
            }
        ]
        self.resources_support_set = resources_support_set
        self.player_initial_resources = player_initial_resources
        self.player_social_behaviour = player_social_behaviour
        self.player_roles = player_roles

        # init players
        self.init_players()

    def init_players(self):
        settings = self.game_state[0]["settings"]
        for idx, player in enumerate(self.players):
            # Simple prompt for simple game
            game_prompt = f"""You are playing a simple trading game.
Resources available: {settings['resources_support_set'].only_keys()}
Your initial resources: {settings['player_initial_resources'][idx]}
{settings['player_social_behaviour'][idx]}
"""
            player.init_agent(game_prompt, settings["player_roles"][idx])

    def game_over(self):
        """
        Game over logic based on game state
        """
        state = self.game_state[-1]
        if state:
            iteration = state.get("current_iteration", 0)
            if iteration >= self.iterations:
                return True
        return False

    def after_game_ends(self):
        initial_resources = self.game_state[0]["settings"]["player_initial_resources"]
        
        # Simple end state logging
        datum = dict(
            current_iteration="END",
            turn="None",
            summary=dict(
                initial_resources=initial_resources,
                game_complete=True,
            ),
        )
        
        self.game_state.append(datum)