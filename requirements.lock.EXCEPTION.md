# requirements.lock — partial-lock exception (W28A-861-R3)

## Status

`requirements.lock` is a **partial lock**. It pins all 39 resolved third-party
runtime dependencies (resolved for python 3.12 against the public index
`https://pypi.org/simple/` with pip-tools), but it **cannot** pin the 9 Cloud-Dog
platform packages, because they are not published to the public index.

## Evidence (verified on server2, python:3.12-slim, 2026-06-07)

`pip index versions <pkg> --index-url https://pypi.org/simple/` returns "missing"
for every platform package:

```
PUBLIC-PYPI MISSING: cloud-dog-config
PUBLIC-PYPI MISSING: cloud-dog-api-kit
PUBLIC-PYPI MISSING: cloud-dog-vdb
PUBLIC-PYPI MISSING: cloud-dog-idam
PUBLIC-PYPI MISSING: cloud-dog-jobs
PUBLIC-PYPI MISSING: cloud-dog-llm
PUBLIC-PYPI MISSING: cloud-dog-storage
PUBLIC-PYPI MISSING: cloud-dog-db
PUBLIC-PYPI MISSING: cloud-dog-logging
```

PS-97 §3.3 / §4 forbid `--extra-index-url` as a fallback. The standard's
prescribed action when a platform package is absent from the boundary index is
to STOP and have the package published into the boundary — NOT to seal a lock
that silently reaches a second index.

## Platform-package version constraints (from `pyproject.toml`, authoritative)

| Package            | Constraint        |
|--------------------|-------------------|
| cloud_dog_config   | >=0.3.1           |
| cloud_dog_logging  | >=0.3.3           |
| cloud_dog_api_kit  | ==0.13.0          |
| cloud_dog_idam     | >=0.4.0           |
| cloud_dog_jobs     | ==0.4.1           |
| cloud_dog_db       | >=0.1.0           |
| cloud_dog_storage  | >=0.1.1           |
| cloud_dog_llm      | ==0.3.0           |
| cloud_dog_vdb      | >=0.5.4           |

## Owner / closure path

Owner: the W28A-86x publication chain (the same lane family that publishes the
platform packages to the Gitea/GitHub public boundary). Once the 9 packages are
published to the chosen public index, regenerate a full sealed lock with:

```bash
PIP_NO_BINARY=lxml,xmlsec pip-compile --strip-extras \
  --index-url "${PYPI_URL:-https://pypi.org/simple/}" \
  --output-file requirements.lock pyproject.toml
```

and delete this exception file.

## What IS sealed today

- All 39 third-party deps are pinned in `requirements.lock` and verifiably
  resolve from the public index for python 3.12.
- Direct platform-package constraints are captured above and in `pyproject.toml`.
- The Docker build (`Dockerfile.public`) installs the platform packages from the
  active index supplied via the `pip_conf` BuildKit secret (single index; no
  `--extra-index-url`), so once the packages exist on the boundary index the
  image builds end-to-end without any code change.
