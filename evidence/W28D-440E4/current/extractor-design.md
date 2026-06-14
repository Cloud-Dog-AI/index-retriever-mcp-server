source_family	UNDP HDRO Data API 2.0
tool_name	hdro_extract
service_surface	IndexService.hdro_extract via mcp_server.execute_tool and REST/A2A shared registry dispatch
config	defaults.hdro.yaml resolves vault.dev.external.HDRO.* through cloud_dog_config; defaults.yaml carries non-secret canonical URL only
endpoint_safety	hdrdata.org/www.hdrdata.org allowed; maptiler Vault URL recorded as defect and not selected; other non-HDRO hosts rejected
request	GET /api/CompositeIndices/query with apikey, countryOrAggregation, year; diagnostics use redacted_request_url
response	JSON list filtered to HDI/GII; returns source metadata, endpoint host/path, country/year records, record counts
errors	HDRORequestError includes host/path/status/response_class/retryable and redacts apikey-like query fragments
secret_policy	no os.environ credential fallback chain; no raw key in logs/evidence/tests; live scan raw_key_hits=0
