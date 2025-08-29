# LLM Release Radar Agent

An intelligent agent that monitors and reports on the latest LLM releases, features, and announcements from major tech companies.

## Overview

The LLM Release Radar Agent automatically:
- Searches for new LLM releases from OpenAI, Google, Microsoft, Anthropic, and others
- Analyzes content using local Qwen LLM for structured information extraction
- Publishes weekly summaries to your Notion workspace
- Runs on Kubernetes with Raspberry Pi 5 optimization

## Quick Start

### Prerequisites
- Python 3.9+
- Docker
- Kubernetes cluster
- Local Ollama server with Qwen model
- Notion integration token

### Setup
```bash
# Install dependencies
make setup

# Configure environment
cp .env.example .env
# Edit .env with your API keys and configuration

# Run tests
make test

# Build Docker image
make build

# Deploy to Kubernetes
make deploy
```

## Development

### Available Commands
```bash
make help           # Show all available commands
make lint           # Run code linting
make test           # Run all tests
make coverage       # Generate coverage report
make build          # Build Docker image
make deploy         # Deploy to Kubernetes
make logs           # View application logs
make debug          # Debug deployment issues
```

### Project Structure
```
llm-release-radar/
├── src/                    # Source code
│   ├── agent/             # Core agent modules
│   ├── clients/           # External service clients
│   ├── models/            # Data models
│   ├── utils/             # Utilities
│   └── config/            # Configuration
├── tests/                 # Tests
├── docker/                # Docker configuration
├── k8s/                   # Kubernetes manifests
└── docs/                  # Documentation
```

## Configuration

Key environment variables:
- `OLLAMA_HOST`: Local LLM server endpoint
- `NOTION_TOKEN`: Notion integration token
- `NOTION_DATABASE_ID`: Target Notion database
- `SEARCH_API_KEY`: Web search API key

See `.env.example` for full configuration options.

## Deployment

The agent is designed to run on Kubernetes with:
- Weekly CronJob execution
- Resource limits optimized for Raspberry Pi 5
- Health checks and monitoring
- Automatic retry and error handling

## Monitoring

The agent provides:
- Health check endpoints
- Prometheus metrics
- Structured logging
- Kubernetes deployment status

## Architecture

See `docs/architecture.md` for detailed system architecture and data flow diagrams.

