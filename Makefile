.PHONY: up up-monitoring down logs logs-processor logs-api test-unit test-all clean

up:  ## Start all pipeline services
	docker compose up --build -d

up-monitoring:  ## Start pipeline + Prometheus + Grafana
	docker compose --profile monitoring up --build -d

down:  ## Stop all services
	docker compose --profile monitoring down

logs:  ## Follow all service logs
	docker compose logs -f

logs-processor:  ## Follow stream processor logs
	docker compose logs -f stream-processor

logs-api:  ## Follow API server logs
	docker compose logs -f api

logs-producers:  ## Follow producer logs
	docker compose logs -f iot-producer activity-producer

test-unit:  ## Run unit tests
	python -m pytest tests/unit -v

test-all:  ## Run all tests
	python -m pytest tests/ -v

clean:  ## Remove all containers, volumes, and pruned images
	docker compose --profile monitoring down -v
	docker system prune -f

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
