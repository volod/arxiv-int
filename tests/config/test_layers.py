"""Tests for layered configuration precedence."""

from arxiv_int.config import merge_config_layers


def test_layers_apply_cli_environment_dotenv_default_precedence() -> None:
    resolved = merge_config_layers(
        {"ROOT": "default", "MODEL": "default", "EMPTY": "default"},
        {"ROOT": "dotenv", "MODEL": "dotenv", "EMPTY": None},
        {"ROOT": "environment"},
        {"ROOT": "cli", "MODEL": None, "EMPTY": ""},
    )

    assert resolved == {"ROOT": "cli", "MODEL": "dotenv", "EMPTY": ""}
