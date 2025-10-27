# openai-image-generation

[![Release](https://img.shields.io/github/v/release/Niopub/openai-image-gen-edit)](https://img.shields.io/github/v/release/Niopub/openai-image-gen-edit)
[![Commit activity](https://img.shields.io/github/commit-activity/m/Niopub/openai-image-gen-edit)](https://img.shields.io/github/commit-activity/m/Niopub/openai-image-gen-edit)
[![License](https://img.shields.io/github/license/Niopub/openai-image-gen-edit)](https://img.shields.io/github/license/Niopub/openai-image-gen-edit)

OpenAI image generation MCP server

- **Github repository**: <https://github.com/Niopub/openai-image-gen-edit/>

## Configuration

```json
{
  "mcpServers": {
    "openai-image-generation": {
      "command": "uvx",
      "args": ["openai-image-gen-edit@latest", "stdio"],
      "env": {
        "OPENAI_API_KEY": "${OPENAI_API_KEY}",
        "OPENAI_BASE_URL": "${OPENAI_BASE_URL}"
      }
    }
  }
}
```

## Docker

Docker image available at: `docker.io/niopub/openai-image-gen-edit`

```bash
docker pull niopub/openai-image-gen-edit:latest
```

### Docker Configuration for MCP

```json
{
  "mcpServers": {
    "openai-image-generation": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "OPENAI_API_KEY=${OPENAI_API_KEY}",
        "niopub/openai-image-gen-edit:latest"
      ]
    }
  }
}
```

### Testing the Docker Image

To test that the Docker image is working correctly, send an MCP initialize message:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | \
  docker run --rm -i -e OPENAI_API_KEY=your-key niopub/openai-image-gen-edit:latest
```

You should see a JSON-RPC response with server capabilities.

**Note:** When run without input, the container will wait for JSON-RPC messages on stdin - this is the expected behavior for MCP servers using stdio transport.

## Using This as a Boilerplate for New MCP Projects

This repository includes a complete build/test/publish workflow for MCP servers. To use it for a new project:

### 1. Copy These Files to Your New Project

```bash
cp Dockerfile your-new-project/
cp .dockerignore your-new-project/
cp Makefile your-new-project/
```

### 2. Update `pyproject.toml`

Update the `name` and `version` fields in your `pyproject.toml`:

```toml
[project]
name = "your-mcp-project-name"
version = "0.1.0"
```

### 3. Update the Dockerfile Entrypoint

In the `Dockerfile`, update line 29 to match your project's command name from `pyproject.toml`:

```dockerfile
ENTRYPOINT ["tini", "--", "uv", "run", "your-mcp-project-name"]
```

### 4. Build, Test, and Publish

```bash
# Build Docker image locally for current platform (fast, for testing)
make docker-build

# Test the image locally with MCP initialize message
make docker-test

# Build multi-platform (linux/amd64, linux/arm64) and push to Docker Hub
# Requires: docker login and Docker buildx
make docker-publish
```

**Optional:** Set a different Docker Hub namespace:

```bash
DOCKER_NAMESPACE=yourusername make docker-build
DOCKER_NAMESPACE=yourusername make docker-test
DOCKER_NAMESPACE=yourusername make docker-publish
```

**Note:** `docker-publish` automatically builds for both AMD64 (x86_64) and ARM64 platforms to ensure compatibility across different architectures.

### 5. Available Make Commands

Run `make help` to see all available commands:

```bash
make install           # Install dependencies and pre-commit hooks
make check             # Run code quality tools
make test              # Run pytest
make build             # Build Python wheel
make publish           # Publish to PyPI
make docker-build      # Build Docker image locally for current platform
make docker-test       # Test Docker image locally
make docker-publish    # Build multi-platform image and push to Docker Hub
```
