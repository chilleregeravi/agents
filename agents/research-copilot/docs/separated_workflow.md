# Separated Research Workflow

## Overview

The Separated Research Workflow is a new architecture that addresses the limitation of local LLM models (like Qwen) not being able to perform internet research. This workflow separates the research process into two distinct phases:

1. **Data Gathering Phase** (External/Manual)
2. **Analysis Phase** (Local LLM)

## Architecture

### Traditional vs Separated Workflow

#### Traditional Workflow (Current)
```
Research Request → LLM Research → Web Scraping → Analysis → Report
```

#### Separated Workflow (New)
```
Research Data Input → Local LLM Analysis → Report
```

### Key Components

#### 1. ResearchData Model
- Represents pre-collected research data
- Supports multiple content types (web pages, documents, news articles, social media)
- Includes quality metrics and metadata

#### 2. SeparatedResearchClient
- Focuses solely on analyzing pre-collected data
- Uses local LLM (Qwen) for content analysis
- Generates insights, trends, and executive summaries
- No internet research capabilities

#### 3. SeparatedResearchCopilotAgent
- Main orchestrator for the separated workflow
- Handles configuration loading and component initialization
- Manages the analysis and publishing phases

#### 4. ResearchDataInput Utilities
- Provides methods to create ResearchData from various sources
- Supports manual input, file uploads, and API integrations
- Includes validation and sample data generation

## Usage

### Basic Usage

```python
from agent.separated_main import SeparatedResearchCopilotAgent
from utils.data_input import ResearchDataInput

# Create research data
research_data = ResearchDataInput.from_manual_input(
    topic_name="AI in Healthcare",
    content_items=[
        {
            "title": "Article Title",
            "content": "Article content...",
            "url": "https://example.com",
            "source_type": "news_articles"
        }
    ]
)

# Initialize agent
agent = SeparatedResearchCopilotAgent()

# Execute analysis
result = await agent.execute_analysis(
    research_data=research_data,
    config_name="RESEARCH_CONFIGURATION_TEMPLATE"
)
```

### Data Input Methods

#### Manual Input
```python
content_items = [
    {
        "title": "Article Title",
        "content": "Article content...",
        "url": "https://example.com",
        "source_type": "news_articles",
        "publication_date": "2024-01-15T00:00:00Z"
    }
]

research_data = ResearchDataInput.from_manual_input(
    topic_name="Research Topic",
    content_items=content_items
)
```

#### File Upload
```python
research_data = ResearchDataInput.from_text_files(
    topic_name="Research Topic",
    file_paths=["file1.txt", "file2.txt"]
)
```

#### API Integration
```python
api_data = {
    "articles": [
        {
            "title": "Article Title",
            "content": "Article content...",
            "url": "https://example.com",
            "published_at": "2024-01-15T00:00:00Z"
        }
    ]
}

research_data = ResearchDataInput.from_api_response(
    topic_name="Research Topic",
    api_data=api_data
)
```

#### JSON File
```python
research_data = ResearchDataInput.from_json_file("research_data.json")
```

### Sample Data
```python
# Create sample data for testing
sample_data = ResearchDataInput.create_sample_data("Sample Topic")
```

## Configuration

The separated workflow uses the same configuration system as the traditional workflow, but focuses on analysis parameters rather than search strategies.

### Analysis Configuration
```python
analysis_request = AnalysisRequest(
    research_data=research_data,
    analysis_config=research_config,
    analysis_focus=["key_insights", "trends", "implications"],
    include_confidence_scores=True,
    include_source_citations=True,
    group_similar_findings=True,
    trend_analysis=True,
    include_quantitative_data=True
)
```

## Output

The separated workflow generates the same types of outputs as the traditional workflow:

- **Executive Summary**: High-level overview of findings
- **Key Insights**: Detailed analysis insights with confidence scores
- **Trend Analysis**: Patterns and trends identified across content
- **Quantitative Findings**: Numerical data and metrics extracted
- **Notion Page**: Formatted report in Notion (if configured)

## Advantages

### 1. Local Processing
- No internet connectivity required for analysis
- Works with local LLM models (Qwen, Llama, etc.)
- Faster processing without network delays

### 2. Data Control
- Complete control over research data sources
- No dependency on external APIs or search engines
- Can include proprietary or internal documents

### 3. Quality Assurance
- Manual review of data sources before analysis
- Better control over data quality and relevance
- Reduced risk of biased or unreliable sources

### 4. Privacy and Security
- No data sent to external services for research
- All processing happens locally
- Suitable for sensitive or confidential research

## Limitations

### 1. Manual Data Collection
- Requires manual effort to gather research data
- No automated web scraping or search
- Limited to pre-collected content

### 2. Coverage Limitations
- Analysis quality depends on data quality
- May miss recent developments not in collected data
- Requires human judgment for data selection

### 3. Time Investment
- Initial data collection takes time
- Requires research skills to identify relevant sources
- Manual validation of data quality

## Use Cases

### 1. Academic Research
- Analysis of research papers and academic literature
- Literature reviews and meta-analyses
- Systematic reviews of existing research

### 2. Market Research
- Analysis of competitor documents and reports
- Review of industry publications and whitepapers
- Analysis of customer feedback and reviews

### 3. Policy Analysis
- Review of government documents and reports
- Analysis of policy papers and recommendations
- Evaluation of regulatory frameworks

### 4. Content Analysis
- Analysis of news articles and media coverage
- Review of social media content and discussions
- Analysis of technical documentation

## Migration from Traditional Workflow

To migrate from the traditional workflow to the separated workflow:

1. **Collect Research Data**: Gather relevant content manually or through APIs
2. **Create ResearchData Object**: Use ResearchDataInput utilities
3. **Update Agent Usage**: Use SeparatedResearchCopilotAgent instead of ResearchCopilotAgent
4. **Configure Analysis**: Set up analysis parameters and focus areas
5. **Execute Analysis**: Run the analysis workflow

## Example Migration

### Before (Traditional)
```python
agent = ResearchCopilotAgent()
result = await agent.execute_research("tech_research_config")
```

### After (Separated)
```python
# Collect data first
research_data = ResearchDataInput.from_manual_input(...)

# Analyze with local LLM
agent = SeparatedResearchCopilotAgent()
result = await agent.execute_analysis(
    research_data=research_data,
    config_name="tech_research_config"
)
```

## Future Enhancements

### 1. Automated Data Collection
- Integration with web scraping tools
- API connectors for news and research sources
- Automated data validation and quality checks

### 2. Enhanced Analysis
- Multi-modal analysis (text, images, videos)
- Advanced trend detection algorithms
- Comparative analysis across multiple datasets

### 3. Collaboration Features
- Shared research data repositories
- Collaborative analysis workflows
- Version control for research data

### 4. Integration Capabilities
- Database connectors for research data
- Cloud storage integration
- Real-time data streaming

## Conclusion

The Separated Research Workflow provides a practical solution for using local LLM models in research applications. While it requires more manual effort in data collection, it offers greater control, privacy, and reliability compared to automated web research approaches.

This architecture is particularly well-suited for:
- Organizations with strict privacy requirements
- Research projects requiring high-quality, curated data
- Environments with limited internet connectivity
- Applications where data control and auditability are important






