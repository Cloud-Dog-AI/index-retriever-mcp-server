# W28D-440E5 HDRO Vault Preflight

READING PROOF
Mandatory Reading: COMPLETE
RULES_REREAD: YES version_sha256=6d3eeb2db34b1ecc11e44f4dad8367127fd1a7f8944ff76493433702e16c92f7
AGENT-LESSONS_REREAD: YES version_sha256=e1a30f9a365dac1d653d2aa8c137c8f56290edce13b12a78e53c104d448b4323
reading_proof_answers_marker=present

timestamp_utc=2026-06-14T21:15:19.905926Z
vault_addr_host=vault0.cloud-dog.net
vault_token_present=True
vault_health_http=429
vault_initialized=True
vault_sealed=False
vault_standby=True
vault_version=1.20.3
vault_health=PASS
vault_config_mount=cloud_dog_ai
vault_config_path=config
vault_config_read=PASS
hdro_vault_path=dev.external.HDRO
hdro_keys_present=api-key,url,username
hdro_key_present=True
hdro_key_len=36
hdro_key_sha256_prefix=673b8c15
hdro_username_set=True
hdro_vault_url_host=maptiler.com
endpoint_config_defect=Vault dev.external.HDRO.url resolves to maptiler.com; it is not used for HDRO
selected_hdro_base_url=https://hdrdata.org
selected_hdro_host=hdrdata.org
canonical_probe_endpoint=https://hdrdata.org/api/CompositeIndices/query?apikey=%3Credacted%3E&countryOrAggregation=AFG&year=2022
canonical_probe_status=200
canonical_probe_bytes=6808
canonical_probe_json=True
canonical_probe_shape=list_len=36
canonical_probe_sample_keys=country,dimension,index,indicator,value,year
canonical_probe_required_keys_present=True
canonical_probe=PASS
C0_ENDPOINT_SAFE=PASS
