# index-retriever-mcp-server — UT1.1
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Tests configuration precedence ordering.

from index_tools.config.loader import merge_config_layers


def test_config_loader_precedence() -> None:
    defaults = {"server": {"http": {"port": 8686}}}
    config = {"server": {"http": {"port": 8688}}}
    dot_env = {"server": {"http": {"port": 8689}}}
    env = {"server": {"http": {"port": 8690}}}
    merged = merge_config_layers(defaults, config, dot_env, env)
    assert merged["server"]["http"]["port"] == 8690
