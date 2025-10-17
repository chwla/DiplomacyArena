from negotiationarena.game_objects.resource import Resources
from negotiationarena.constants import *
from negotiationarena.utils import *
from negotiationarena.agent_message import AgentMessageInterface
from negotiationarena.parser import ExchangeGameDefaultParser


class SimpleGameAgentMessage(AgentMessageInterface):
    """
    Structured format for agent messages in SimpleGame.
    """
    def message_to_other_player(self):
        message = self.public.get(MESSAGE_TAG, "")
        answer = self.public.get(PLAYER_ANSWER_TAG, "")
        trade = self.public.get(PROPOSED_TRADE_TAG, "")

        r = f"""<{OTHER_PLAYER_MESSAGE}> {message} </{OTHER_PLAYER_MESSAGE}>
<{OTHER_PLAYER_ANSWER}> {answer} </{OTHER_PLAYER_ANSWER}>
<{OTHER_PLAYER_PROPOSED_TRADE}> {trade} </{OTHER_PLAYER_PROPOSED_TRADE}>
"""
        return r


class SimpleGameDefaultParser(ExchangeGameDefaultParser):
    def __init__(self):
        super().__init__()

    def instantiate_prompt(
        self,
        agent_name,
        resources_in_game,
        initial_resources,
        social_behaviour,
    ):
        prompt = f"""You are {agent_name} playing a simple trading game.

GAME SETUP:
- Resources available in the game: {resources_in_game}
- Your initial resources: {initial_resources}
- Other players may have different resources

YOUR TASK:
- Negotiate and trade with other players
- Try to improve your resource position
- Make proposals and respond to offers

{social_behaviour}

RESPONSE FORMAT:
You must respond using these XML tags:

<{MY_NAME_TAG}> {agent_name} </{MY_NAME_TAG}>
<{RESOURCES_TAG}> Your current resources </{RESOURCES_TAG}>
<{REASONING_TAG}> Your reasoning for this action </{REASONING_TAG}>
<{PLAYER_ANSWER_TAG}> PROPOSAL or ACCEPT or REFUSE </{PLAYER_ANSWER_TAG}>
<{PROPOSED_TRADE_TAG}> Player X Gives ResourceName: Amount | Player Y Gives ResourceName: Amount </{PROPOSED_TRADE_TAG}>
<{MESSAGE_TAG}> Your message to the other player </{MESSAGE_TAG}>

IMPORTANT:
- Use PROPOSAL when suggesting a trade
- Use ACCEPT when accepting a trade
- Use REFUSE when rejecting a trade
- Always include all required tags in your response
"""
        return prompt

    def parse(self, response):
        ms = SimpleGameAgentMessage()

        # Parse all fields with safe defaults
        try:
            resources = Resources.from_string(
                get_tag_contents(response, RESOURCES_TAG)
            )
        except:
            resources = Resources({})

        answer = get_tag_contents(response, PLAYER_ANSWER_TAG)
        reasoning = get_tag_contents(response, REASONING_TAG)
        message = get_tag_contents(response, MESSAGE_TAG)
        my_name = get_tag_contents(response, MY_NAME_TAG)
        
        try:
            trade = self.parse_trade(response, PROPOSED_TRADE_TAG)
        except:
            trade = None

        # Add to message structure
        ms.add_public(MESSAGE_TAG, message)
        ms.add_public(PLAYER_ANSWER_TAG, answer if answer else "NONE")
        ms.add_public(PROPOSED_TRADE_TAG, trade if trade else "NONE")

        ms.add_secret(RESOURCES_TAG, resources)
        ms.add_secret(MY_NAME_TAG, my_name)
        ms.add_secret(REASONING_TAG, reasoning)

        return ms