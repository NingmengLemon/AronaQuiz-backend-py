
<h1 align="center">
    <img src="images/arona_quiz_logo.png" width="150" height="150" alt="banner" /><br>
    <em>Arona Quiz</em>
</h1>

(Backend part, written in Python)

> Dev not finished yet, plz wait...

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
