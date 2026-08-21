from __future__ import annotations

import json
from pathlib import Path

from data.ingestion import negotiation_cell, profile_and_ingest


def test_incremental_ingestion(tmp_path: Path) -> None:
    game_dir = tmp_path / "0" / "A" / "game-id"
    game_dir.mkdir(parents=True)
    config = {
        "game_type": "negotiation",
        "game_args": {
            "seller_value": 1.0,
            "buyer_value": 1.5,
            "product_price_order": 1000,
            "max_rounds": 10,
            "messages_allowed": True,
            "complete_information": False,
        },
    }
    (game_dir / "config.json").write_text(json.dumps(config))
    (game_dir / "game.csv").write_text(
        "message,product_price,player,round,decision\nask,1200,Alice,1,\n"
    )
    games, profile = profile_and_ingest(tmp_path, source_stratum="human_vs_llm")
    assert profile.games == 1
    assert profile.files == 2
    assert games[0].turns[0]["product_price"] == "1200"
    assert games[0].cell == negotiation_cell(config["game_args"])
