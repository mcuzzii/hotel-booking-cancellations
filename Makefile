.PHONY: up down notebook shell build

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

notebook:
	docker compose exec app uv run jupyter server \
		--ip=0.0.0.0 \
		--port=8888 \
		--no-browser \
		--allow-root

shell:
	docker compose exec app bash