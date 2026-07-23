.PHONY: dev-backend dev-worker dev-frontend up down logs

dev-backend:
	cd backend && fastapi dev app/main.py --host 0.0.0.0 --port 8000

dev-worker:
	cd backend && python -m app.worker

dev-frontend:
	cd frontend && npm run dev

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f
