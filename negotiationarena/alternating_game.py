import os
import time
import json
from negotiationarena.constants import ACCEPTING_TAG, MESSAGE_TAG, PROPOSED_TRADE_TAG, PLAYER_ANSWER_TAG
import inspect
from pathlib import Path
from typing import List
from abc import ABC, abstractmethod, abstractproperty
from negotiationarena.game_objects.game import Game
from negotiationarena.agents.agents import Agent
from negotiationarena.utils import get_next_filename


class AlternatingGame(Game):
    def __init__(
        self,
        players: List[List],
        log_dir: str = ".logs",
        log_path=None,
        iterations: int = 8,
    ):
        super().__init__(players=players, log_dir=log_dir, log_path=log_path)
        self.turn = 0
        self.game_state = []
        self.iterations = iterations
        self.current_iteration = 1
        self.game_interface = None

    @abstractmethod
    def game_over(self):
        pass

    @abstractmethod
    def after_game_ends(self):
        pass

    def read_iteration_message(self, iteration):
        """
        FIXED: Returns structured text observation instead of raw XML
        """
        if iteration < 0 or iteration >= len(self.game_state):
            return {}
        
        datum = self.game_state[iteration]
        public_info = datum.get("player_public_info_dict", {})
        
        # Extract components
        message = public_info.get(MESSAGE_TAG, "")
        proposed_trade = public_info.get(PROPOSED_TRADE_TAG, "")
        player_answer = public_info.get(PLAYER_ANSWER_TAG, "")
        
        # Build clean structured text observation (NOT XML)
        if not message and not proposed_trade:
            return {}
        
        observation_parts = []
        
        if message:
            observation_parts.append(f"Opponent says: {message}")
        
        if proposed_trade and str(proposed_trade) != "NONE":
            observation_parts.append(f"Opponent's proposal: {proposed_trade}")
        
        if player_answer and player_answer != "NONE":
            observation_parts.append(f"Opponent's answer: {player_answer}")
        
        return "\n".join(observation_parts) if observation_parts else {}

    def write_game_state(self, players, response):
        try:
            agent_message = self.game_interface.parse(response)
        except Exception as e:
            print("response : {}".format(response))
            raise e

        datum = dict(
            current_iteration=self.current_iteration,
            turn=self.turn,
            player_public_answer_string=agent_message.message_to_other_player(),
            player_public_info_dict=agent_message.public,
            player_private_info_dict=agent_message.secret,
            player_complete_answer=response,
            player_state=[player.get_state() for player in players],
        )

        self.game_state.append(datum)

    def set_game_state(self, game_state_dict):
        self.run_epoch_time_ms = game_state_dict["run_epoch_time_ms"]
        self.game_state = game_state_dict["game_state"]
        self.players = game_state_dict["players"]
        last_state = self.game_state[-1]
        self.turn = last_state["turn"]
        self.current_iteration = last_state["current_iteration"]

    def get_next_player(self):
        if self.turn == None:
            self.turn = 0
        self.turn = 1 - self.turn

    def view_state(self, iteration=-1, ignore=[]):
        print("State:")
        for k, v in self.game_state[iteration].items():
            if k not in ignore:
                print(k, ":", v)

    def resume(self, iteration: int, log_dir: str = None, fname: str = None):
        if log_dir:
            self.log_dir = os.path.abspath(log_dir)

        if not fname:
            fname = self.run_epoch_time_ms

        self.log_path = os.path.join(
            self.log_dir, get_next_filename(fname, folder=self.log_dir)
        )
        Path(self.log_path).mkdir(parents=True, exist_ok=True)

        if iteration > len(self.game_state) and iteration > 0:
            raise ValueError(
                "Invalid Iteration, Resume Iteration = ({}); Current Iteration = ({})".format(
                    iteration, self.iteration
                )
            )

        self.current_iteration = iteration
        self.turn = self.game_state[iteration - 1]["turn"]
        last_response = self.game_state[iteration - 1]["player_state"][
            self.turn
        ]["conversation"][-1]["content"]
        self.players = [
            Agent.from_dict(player)
            for player in self.game_state[iteration - 1]["player_state"]
        ]
        self.game_state = self.game_state[: iteration - 1]
        self.write_game_state(self.players, last_response)
        self.get_next_player()

    def run(self):
        self.log_state()
        for iteration in range(self.current_iteration, self.iterations + 1):
            self.current_iteration = iteration
            message = self.read_iteration_message(iteration - 1)
            response = self.players[self.turn].step(message)
            self.write_game_state(self.players, response)
            self.view_state(
                ignore=[
                    "player_public_answer_string",
                    "player_public_info_dict",
                    "player_private_info_dict",
                    "player_state",
                ]
            )
            self.log_state()
            if self.game_over():
                self.after_game_ends()
                self.log_state()
                return
            self.get_next_player()
            print("=============\n")

    def log_human_readable_state(self):
        settings = self.game_state[0]["settings"]
        log_str = "Game Settings\n\n"
        for idx, player_settings in enumerate(
            zip(
                *[
                    [(k, str(p)) for p in v]
                    for k, v in settings.items()
                    if isinstance(v, list)
                ]
            )
        ):
            log_str += "Player {} Settings:\n".format(idx + 1)
            log_str += "\n".join(
                ["\t{}: {}".format(_[0], _[1]) for _ in player_settings]
            )
            log_str += "\n\n"
        log_str += "------------------ \n"

        for state in self.game_state[1:]:
            if state["current_iteration"] == "END":
                continue
            data = [
                "Current Iteration: {}".format(state["current_iteration"]),
                "Turn: {}".format(state["turn"]),
                *[
                    "{}: {}".format(k, v)
                    for k, v in {
                        **state["player_public_info_dict"],
                        **state["player_private_info_dict"],
                    }.items()
                ],
            ]
            log_str += "\n".join(data)
            log_str += "\n\n"

        log_str += "------------------ \n"
        if self.game_state[-1]["current_iteration"] == "END":
            state = self.game_state[-1]
            if "summary" in state:
                data = [
                    "Current Iteration: {}".format(state["current_iteration"]),
                    "Turn: {}".format(state["turn"]),
                    *[
                        "{}: {}".format(k, v)
                        for k, v in state["summary"].items()
                    ],
                ]
                log_str += "\n".join(data)

        with open(os.path.join(self.log_path, "interaction.log"), "w") as f:
            f.write(log_str)


class AlternatingGameEndsOnTag(AlternatingGame):
    def __init__(
        self, players: List[List], log_dir=".logs", log_path=None, iterations=8
    ):
        super().__init__(
            players=players,
            log_dir=log_dir,
            log_path=log_path,
            iterations=iterations,
        )
        self.end_tag = ACCEPTING_TAG

    def game_over(self):
        state = self.game_state[-1]
        if state:
            response = state["player_public_info_dict"].get(PLAYER_ANSWER_TAG)
            iteration = state.get("current_iteration", 0)
            if response == self.end_tag or iteration == self.iterations:
                return True
        return False