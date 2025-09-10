# Arona Quiz - Backend

Arona Quiz

(Backend, written in Python)

## Deploy

install [uv](https://docs.astral.sh/uv/)

clone this repo, cd into root dir of proj

```bash
uv sync --no-dev
uv run fastapi run src/app
```

serve yourself to add more args

## Dev & Test

clone, cd

```bash
uv sync --all-groups
```

`data/example_data.*` are provided as test materials.

run test:

```bash
uv run pytest
```
