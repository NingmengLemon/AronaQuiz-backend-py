
<h1 align="center">
    <img src="images/arona_quiz_logo_rounded.png" width="150" height="150" alt="logo" /><br>
    <em>Arona Quiz</em>
</h1>

(Backend part, written in Python)

> Dev not finished yet, plz wait...

## Deploy

1. Install [uv](https://docs.astral.sh/uv/)

2. Clone this repo, `cd` into root dir of proj

3. Install dependencies:

   ```bash
   uv sync --no-dev
   ```

4. Configure database url. For example, write `.env` like this:

   ```dotenv
   database_url=sqlite+aiosqlite:///database.db
   ```

5. Migrate or init database:

   ```bash
   uv run alembic upgrade head
   ```

6. Run app:

   ```bash
   uv run fastapi run src/app
   ```

Serve yourself to add more args & settings

## Dev & Test

1. Clone repo, cd into root dir

2. Install dependencies, including `dev` group

   ```bash
   uv sync --all-groups
   ```

- Run test:

   ```bash
   uv run pytest
   ```

   > `data/example_data.*` are provided as test materials.

- Create an alembic revision:

   ```bash
   uv run alembic revision --autogenerate -m "revision name"
   ```
