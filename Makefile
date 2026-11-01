.PHONY: install-backend install-frontend fetch-data test-backend lint-frontend dev-backend dev-frontend build-frontend docker-up docker-down ci

install-backend:
	python -m pip install -r backend/requirements.txt pytest httpx

install-frontend:
	cd frontend && npm install --no-audit --no-fund

fetch-data:
	python scripts/fetch_data.py

test-backend:
	python -m pytest backend/tests -q

lint-frontend:
	cd frontend && npm run lint

dev-backend:  ## http://localhost:8000 (docs at /docs)
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend:  ## http://localhost:5173
	cd frontend && npm run dev

build-frontend:
	cd frontend && npm run build

docker-up:
	docker compose up --build

docker-down:
	docker compose down

ci: test-backend lint-frontend build-frontend
