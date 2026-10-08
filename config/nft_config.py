import json
from pathlib import Path


CONFIG_FILE = Path(__file__).with_name(
    "nft_config.json"
)


def load_config():
    if not CONFIG_FILE.exists():
        return {
            "contract_address": None,
            "mint_function": None,
            "mint_price_eth": 0,
            "mint_quantity": 1
        }

    with open(
        CONFIG_FILE,
        "r",
        encoding="utf-8"
    ) as f:
        return json.load(f)


def save_config(config):
    with open(
        CONFIG_FILE,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            config,
            f,
            indent=4
        )