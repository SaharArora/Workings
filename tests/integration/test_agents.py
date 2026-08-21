from communication.strategic import render
from leaderboard.agent import LeaderboardAgent
from research.agent import EGSPMAgent, IBOAgent
from leaderboard.policy_router import PolicyRouter


def negotiation_game() -> dict:
    return {
        "game_family": "negotiation", "your_player": "player_1", "phase": "offer",
        "opponent": {"type": "hidden", "name": None},
        "game_state": {"current_player": "player_1", "player_1_role": "seller",
            "player_2_role": "buyer", "player_1_value": 10, "player_2_value": 20,
            "complete_information": True, "horizon_known": True, "max_rounds": 1,
            "messages_allowed": True},
        "valid_actions": {"type": "offer", "fields": {"product_price": "number", "message": "string"}},
    }


def test_strategic_renderer_does_not_change_economic_fields() -> None:
    action = {"product_price": 20}
    rendered = render(action, negotiation_game())
    assert {key: value for key, value in rendered.items() if key != "message"} == action


def test_research_variants_use_identical_neutral_message() -> None:
    game = negotiation_game()
    assert IBOAgent().decide(game)["message"] == EGSPMAgent(PolicyRouter()).decide(game)["message"]


def test_leaderboard_attaches_language_after_price() -> None:
    result = LeaderboardAgent().decide(negotiation_game())
    assert result["product_price"] == 20
    assert "message" in result
