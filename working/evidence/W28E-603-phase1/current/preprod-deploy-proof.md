# W28E-603 — preprod deploy proof
Date context: 2026-06-05. Approved path: build (server2) -> push registry -> terraform apply targeted (server0).
Image built sha256:14e1eab439f3... pushed registry.cloud-dog.net:443/cloud-dog/index-retriever-mcp-server@sha256:e0124cca...
Terraform dir: .w28a936-cloud-dog-repo/terraform/server0.viewdeck.com/27 MLAgents/
Targeted plan: -target=docker_image.indexretriever -target=docker_container.indexretriever0 => Plan: 2 add, 0 change, 2 destroy (ONLY indexretriever; no sibling services touched).
Apply: 'Apply complete! Resources: 2 added, 0 changed, 2 destroyed.'  container id d624f49f...  image now sha256:14e1eab4 (matches build).
