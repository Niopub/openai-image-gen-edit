.PHONY: install
install: ## Install the virtual environment and install the pre-commit hooks
	@echo "🚀 Creating virtual environment using uv"
	@uv sync
	@uv run pre-commit install

.PHONY: check
check: ## Run code quality tools.
	@echo "🚀 Checking lock file consistency with 'pyproject.toml'"
	@uv lock --locked
	@echo "🚀 Linting code: Running pre-commit"
	@uv run pre-commit run -a
	@echo "🚀 Checking for obsolete dependencies: Running deptry"
	@uv run deptry .

.PHONY: test
test: ## Test the code with pytest
	@echo "🚀 Testing code: Running pytest"
	@uv run python -m pytest --cov --cov-config=pyproject.toml --cov-report=xml

.PHONY: build
build: clean-build ## Build wheel file
	@echo "🚀 Creating wheel file"
	@uvx --from build pyproject-build --installer uv

.PHONY: clean-build
clean-build: ## Clean build artifacts
	@echo "🚀 Removing build artifacts"
	@uv run python -c "import shutil; import os; shutil.rmtree('dist') if os.path.exists('dist') else None"

.PHONY: publish
publish: ## Publish a release to PyPI.
	@echo "🚀 Publishing."
	@uvx twine upload --repository-url https://upload.pypi.org/legacy/ dist/*

.PHONY: build-and-publish
build-and-publish: build publish ## Build and publish.

.PHONY: docs-test
docs-test: ## Test if documentation can be built without warnings or errors
	@uv run mkdocs build -s

.PHONY: docs
docs: ## Build and serve the documentation
	@uv run mkdocs serve

.PHONY: docker-build
docker-build: ## Build Docker image (uses project name and version from pyproject.toml)
	@echo "🚀 Building Docker image..."
	@DOCKER_NAMESPACE=$${DOCKER_NAMESPACE:-niopub}; \
	PROJECT_NAME=$$(grep '^name = ' pyproject.toml | cut -d'"' -f2); \
	VERSION=$$(grep '^version = ' pyproject.toml | cut -d'"' -f2); \
	docker build -t $$DOCKER_NAMESPACE/$$PROJECT_NAME:latest -t $$DOCKER_NAMESPACE/$$PROJECT_NAME:$$VERSION .
	@echo "✅ Image built successfully"

.PHONY: docker-test
docker-test: ## Test Docker image locally with MCP initialize message
	@echo "🚀 Testing Docker image..."
	@DOCKER_NAMESPACE=$${DOCKER_NAMESPACE:-niopub}; \
	PROJECT_NAME=$$(grep '^name = ' pyproject.toml | cut -d'"' -f2); \
	echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"0.1.0","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | \
	docker run --rm -i -e OPENAI_API_KEY=test-key $$DOCKER_NAMESPACE/$$PROJECT_NAME:latest 2>&1 | head -5
	@echo "✅ Docker test completed"

.PHONY: docker-publish
docker-publish: ## Push Docker image to Docker Hub
	@echo "🚀 Pushing Docker image to Docker Hub..."
	@DOCKER_NAMESPACE=$${DOCKER_NAMESPACE:-niopub}; \
	PROJECT_NAME=$$(grep '^name = ' pyproject.toml | cut -d'"' -f2); \
	VERSION=$$(grep '^version = ' pyproject.toml | cut -d'"' -f2); \
	docker push $$DOCKER_NAMESPACE/$$PROJECT_NAME:latest && \
	docker push $$DOCKER_NAMESPACE/$$PROJECT_NAME:$$VERSION && \
	echo "✅ Image pushed to: https://hub.docker.com/r/$$DOCKER_NAMESPACE/$$PROJECT_NAME"

.PHONY: help
help:
	@uv run python -c "import re; \
	[[print(f'\033[36m{m[0]:<20}\033[0m {m[1]}') for m in re.findall(r'^([a-zA-Z_-]+):.*?## (.*)$$', open(makefile).read(), re.M)] for makefile in ('$(MAKEFILE_LIST)').strip().split()]"

.DEFAULT_GOAL := help
