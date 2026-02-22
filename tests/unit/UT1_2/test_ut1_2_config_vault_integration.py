# index-retriever-mcp-server — UT1.2
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Tests config merge including vault-like overlay.

from index_tools.config.loader import merge_config_layers


def test_config_vault_overlay() -> None:
    defaults = {"profiles": {"default": {"embeddings": {"openai_compat": {"api_key": "x"}}}}}
    vault = {"profiles": {"default": {"embeddings": {"openai_compat": {"api_key": "vault-key"}}}}}
    merged = merge_config_layers(defaults_layer=defaults, config_layer=vault)
    assert merged["profiles"]["default"]["embeddings"]["openai_compat"]["api_key"] == "vault-key"
