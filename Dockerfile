FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.9.0 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project
COPY . .
RUN uv sync --frozen --no-dev
# rembg downloads its model (~180 MB) on first use; bake it into the image
RUN uv run python -c "from rembg import new_session; new_session('isnet-general-use')"
ENTRYPOINT ["uv", "run", "recept"]
CMD ["run", "--brief", "inputs/brief.yaml", "--yes"]
