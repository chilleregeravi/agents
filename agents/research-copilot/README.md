# Research Copilot Agent

An intelligent agent that performs configurable research on any topic and generates structured reports using local LLM models.

## Overview

The Research Copilot Agent provides three workflow options:

### 1. Traditional Workflow (Internet Research)
- Automatically searches for information using web APIs
- Analyzes content using local Qwen LLM for structured information extraction
- Publishes reports to your Notion workspace
- Runs on Kubernetes with Raspberry Pi 5 optimization

### 2. Separated Workflow (Local Analysis)
- Accepts pre-collected research data from various sources
- Performs analysis using local Qwen LLM without internet access
- Generates insights, trends, and executive summaries
- Ideal for privacy-sensitive or curated research projects

### 3. Comprehensive Workflow (Complete Automation)
- **Research Request → Scrape internet by agent based on what sites should be scraped**
- **Collect data by agent and provide to LLM with context of research request**
- **LLM generates output based on the data**
- **Send data to Notion**
- Fully automated end-to-end research pipeline

## Quick Start

### Prerequisites
- Python 3.9+
- Docker
- Kubernetes cluster (for traditional workflow)
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

# Deploy to Kubernetes (traditional workflow)
make deploy
```

## Usage Examples

### Traditional Workflow (Internet Research)
```python
from agent.main import ResearchCopilotAgent

agent = ResearchCopilotAgent()
result = await agent.execute_research("tech_research_config")
```

### Separated Workflow (Local Analysis)
```python
from agent.separated_main import SeparatedResearchCopilotAgent
from utils.data_input import ResearchDataInput

# Create research data
research_data = ResearchDataInput.from_manual_input(
    topic_name="AI in Healthcare",
    content_items=[...]
)

# Analyze with local LLM
agent = SeparatedResearchCopilotAgent()
result = await agent.execute_analysis(
    research_data=research_data,
    config_name="healthcare_research_config"
)
```

### Comprehensive Workflow (Complete Automation)
```python
from agent.comprehensive_main import ComprehensiveResearchCopilotAgent

# Complete automated research pipeline
agent = ComprehensiveResearchCopilotAgent()
result = await agent.execute_comprehensive_research(
    config_name="tech_research_config",
    override_params={
        "max_sources": 20,
        "credibility_threshold": 0.8
    }
)
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
research-copilot/
├── src/                    # Source code
│   ├── agent/             # Core agent modules
│   │   ├── main.py        # Traditional workflow agent
│   │   ├── separated_main.py # Separated workflow agent
│   │   └── comprehensive_main.py # Comprehensive workflow agent
│   ├── clients/           # External service clients
│   │   ├── llm_researcher.py # Traditional research client
│   │   ├── separated_research_client.py # Local analysis client
│   │   └── comprehensive_research_client.py # Complete workflow client
│   ├── models/            # Data models
│   ├── utils/             # Utilities
│   │   └── data_input.py  # Data input utilities
│   └── config/            # Configuration
├── tests/                 # Tests
├── docker/                # Docker configuration
├── k8s/                   # Kubernetes manifests
├── examples/              # Usage examples
└── docs/                  # Documentation
```

## Configuration

Key environment variables:
- `OLLAMA_HOST`: Local LLM server endpoint
- `NOTION_TOKEN`: Notion integration token
- `NOTION_DATABASE_ID`: Target Notion database
- `SEARCH_API_KEY`: Web search API key (traditional workflow only)

See `.env.example` for full configuration options.

## Workflow Comparison

| Feature | Traditional Workflow | Separated Workflow | Comprehensive Workflow |
|---------|-------------------|-------------------|----------------------|
| Internet Access | Required | Not required | Required |
| Data Collection | Automated APIs | Manual/External | Automated scraping |
| Privacy | Limited | High | Limited |
| Speed | Network dependent | Local processing | Network dependent |
| Data Control | Limited | Complete | Limited |
| Automation | Partial | Manual | Full |
| Use Cases | General research | Curated research | Complete automation |

## Deployment

### Traditional Workflow
The agent is designed to run on Kubernetes with:
- Weekly CronJob execution
- Resource limits optimized for Raspberry Pi 5
- Health checks and monitoring
- Automatic retry and error handling

### Separated Workflow
Can run locally or in containers:
- No internet connectivity required
- Local processing only
- Suitable for air-gapped environments
- Flexible deployment options

### Comprehensive Workflow
Full automation pipeline:
- Internet scraping capabilities
- Local LLM analysis
- Automated data collection and processing
- Complete end-to-end research automation

## Monitoring

The agent provides:
- Health check endpoints
- Prometheus metrics
- Structured logging
- Kubernetes deployment status (traditional workflow)

## Documentation

- [Architecture Overview](docs/architecture.md)
- [Separated Workflow Guide](docs/separated_workflow.md)
- [Comprehensive Workflow Guide](docs/comprehensive_workflow.md)
- [Configuration Reference](docs/configuration.md)
- [API Documentation](docs/api.md)

## Examples

See the `examples/` directory for:
- [Separated Workflow Example](examples/separated_workflow_example.py)
- [Comprehensive Workflow Example](examples/comprehensive_workflow_example.py)
- Configuration templates
- Data input examples

## Workflow Flow Diagrams

### Comprehensive Workflow
```
Research Request → Generate Scraping Strategy → Scrape Internet → 
Collect Data → Organize Data → Provide to LLM with Context → 
Generate Analysis → Create Notion Page → Publish Results
```

### Separated Workflow
```
Research Data Input → Preprocess Data → Local LLM Analysis → 
Generate Insights → Create Notion Page → Publish Results
```

### Traditional Workflow
```
Research Request → Web API Search → Content Analysis → 
Generate Insights → Create Notion Page → Publish Results
```

