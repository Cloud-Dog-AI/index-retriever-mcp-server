# W28D-440E4 HDRO Vault Preflight

timestamp_utc=2026-06-14T19:23:46.627544Z
vault_addr_host=vault0.cloud-dog.net
vault_token_present=True
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
