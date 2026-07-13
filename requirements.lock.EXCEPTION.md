# requirements.lock — partial-lock exception: CLOSED (W28A-861-R3)

## Status: RESOLVED — exception withdrawn

`requirements.lock` is now a **full sealed lock**. The 9 Cloud-Dog platform
packages are pinned alongside the 39 third-party packages. The partial-lock
exception that previously applied is **closed**.

## Why the exception is closed

The earlier exception claimed the platform packages "cannot be pinned" because
they were absent from `https://pypi.org/simple/`. That was the **wrong
boundary** for the 861-R3 clean-room (main/local) build. The main/local build
uses the **internal** index `https://pypi.cloud-dog.net/simple/`, where all 9
platform packages are published and resolve end-to-end. Public pypi.org is a
downstream concern owned by the W28A-862/863 publication chain, not a blocker
for this build.

## Evidence (verified on server2, python:3.12-slim, 2026-06-08)

All 9 platform packages are present on the internal index and were installed
into a GREEN `Dockerfile.public` build (exit 0). Resolved versions, read back
from the built image:

```
cloud-dog-config==0.3.2
cloud-dog-logging==0.4.0
cloud-dog-api-kit==0.13.0
cloud-dog-idam==0.4.0
cloud-dog-db==0.3.0
cloud-dog-jobs==0.4.1
cloud-dog-storage==0.1.8
cloud-dog-llm==0.3.0
cloud-dog-vdb==0.5.5
```

Build evidence: `working/evidence/W28A-861-R3-index-retriever/build-main-local.log`
(image `sha256:43d04fb0798d21ea80551c5aacf0f74c1aa5de85b0fc6738c0701fe21b3db7aa`).

## Index-agnostic by construction

`requirements.lock` pins versions only — no index URL, no `--extra-index-url`,
no credentials (PS-97 §3.3 single-index honoured). The active index is supplied
at install time via the `pip_conf` BuildKit secret in `Dockerfile.public`. The
same pins resolve unchanged against any index that carries these versions;
when the platform packages are also published to the public boundary index
(W28A-862/863), no change to this lock is required.

## Downstream (public pypi.org) — out of scope for R3

Pinning/resolving these platform packages from the **public** boundary index
remains owned by the W28A-862/863 publication chain (publish platform packages
to the public boundary). That is a separate, downstream lane and does NOT block
the main/local sealed lock delivered here.
