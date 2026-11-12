.PHONY: build up down initialize notebook download shell

build:
	docker compose run --rm pydev sh -c '\
		uv init --no-package && \
		uv add jupyter-server ipykernel'

up:
	docker compose up -d

down:
	docker compose down

initialize:
	docker compose exec pydev sh -c '\
		uv sync --frozen --no-install-project && \
		uv run python -m ipykernel install \
			--sys-prefix \
			--name pydev \
			--display-name "Python (Docker)"'

notebook:
	docker compose exec pydev uv run jupyter server \
		--ip=0.0.0.0 \
		--port=8888 \
		--no-browser \
		--allow-root

download:
	docker compose exec pydev uv run src/download.py

shell:
	docker compose exec pydev bash