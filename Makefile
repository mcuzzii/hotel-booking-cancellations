.PHONY: up down notebook download shell build

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

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