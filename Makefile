.PHONY: help install test lint clean run dev

# Default target
help:
	@echo "NixMind Development Commands:"
	@echo "  install    - Install dependencies and package"
	@echo "  test       - Run unit tests"
	@echo "  lint       - Run code linting"
	@echo "  clean      - Clean build artifacts"
	@echo "  run        - Run NixMind CLI"
	@echo "  dev        - Install in development mode"

# Install dependencies and package
install:
	pip install -r requirements.txt
	pip install -e .

# Install in development mode
dev:
	pip install -r requirements.txt
	pip install -e .

# Run unit tests
test:
	python -m pytest tests/unit/ -v

# Alternative test runner for async tests
test-simple:
	python -m unittest discover tests/unit/ -v

# Run linting (if available)
lint:
	@command -v flake8 >/dev/null 2>&1 && flake8 src/ || echo "flake8 not installed, skipping lint"
	@command -v pylint >/dev/null 2>&1 && pylint src/nixmind/ || echo "pylint not installed, skipping lint"

# Clean build artifacts
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/

# Run NixMind CLI
run:
	python main.py

# Check if Ollama is running
check-ollama:
	@curl -s http://localhost:11434/api/tags >/dev/null && echo "✅ Ollama is running" || echo "❌ Ollama is not running - please start it with: systemctl start ollama"

# Development setup
setup: install check-ollama
	@echo "✅ Development environment ready!"
	@echo "Run 'make run' to start NixMind"

# Build package
build:
	python setup.py sdist bdist_wheel

# Show project structure
tree:
	tree -I '__pycache__|*.pyc|*.egg-info|.git'