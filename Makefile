.PHONY: help dev install backend web clean

help:
	@echo "AI 热点洞察 Agent 平台"
	@echo ""
	@echo "  make install     Install all dependencies"
	@echo "  make dev         Start backend (requires uvicorn)"
	@echo "  make dev-full    Start backend + frontend"
	@echo "  make web         Start frontend dev server"
	@echo "  make docker      Start via Docker Compose"
	@echo "  make clean       Remove generated files"

install:
	cd backend && pip install -r requirements.txt
	cd web && npm install

dev:
	cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000

web:
	cd web && npm run dev

dev-full:
	@echo "Starting backend and frontend..."
	cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
	cd web && npm run dev

docker:
	docker-compose up --build

clean:
	find backend -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find backend -type f -name "*.pyc" -delete
	rm -rf data/agent.db
