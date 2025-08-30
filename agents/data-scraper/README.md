# Data Scraper Agent

A powerful, configurable API scraping agent that can extract data from various APIs using YAML configuration files and environment variables for authentication.

## Features

- **Configuration-Driven**: Define API endpoints, authentication, and data transformations in YAML files
- **Environment Variable Authentication**: Secure credential management using environment variables
- **Rate Limiting**: Built-in rate limiting to respect API limits
- **Data Transformation**: Field mapping, filtering, and validation
- **Multiple Output Formats**: JSON, CSV, and more
- **Async Processing**: High-performance async HTTP requests
- **Retry Logic**: Automatic retry with exponential backoff
- **Comprehensive Logging**: Detailed logging for monitoring and debugging
- **Container Ready**: Docker support for easy deployment

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd agents/data-scraper

# Install dependencies
pip install -r requirements.txt
```

### 2. Create Configuration

Create a configuration file in `/app/config/apis/` (or your config path):

```yaml
# config/apis/my-api.yaml
name: "My API Scraper"
description: "Scrape data from my API"
base_url: "https://api.example.com"
authentication:
  type: "bearer_token"
  bearer_token: "$MY_API_TOKEN"  # Environment variable

endpoints:
  - name: "users"
    url: "/users"
    method: "GET"
    headers:
      Accept: "application/json"
    timeout: 30
    retry_attempts: 3

rate_limit:
  requests_per_minute: 60
  requests_per_hour: 1000
  delay_between_requests: 1.0

transformation:
  field_mapping:
    id: "user_id"
    name: "user_name"
    email: "user_email"

output_config:
  format: "json"
  filename: "users_data"
```

### 3. Set Environment Variables

```bash
export MY_API_TOKEN="your-api-token-here"
```

### 4. Run the Scraper

```bash
# Execute scraping job
python -m agent.main scrape --config my-api

# List available configurations
python -m agent.main list

# Validate configuration
python -m agent.main validate --config my-api
```

## Configuration Reference

### Authentication Types

#### Bearer Token
```yaml
authentication:
  type: "bearer_token"
  bearer_token: "$API_TOKEN"
```

#### API Key
```yaml
authentication:
  type: "api_key"
  api_key_name: "X-API-Key"
  api_key_value: "$API_KEY"
```

#### Basic Auth
```yaml
authentication:
  type: "basic_auth"
  username: "$API_USERNAME"
  password: "$API_PASSWORD"
```

#### No Authentication
```yaml
authentication:
  type: "none"
```

### Endpoint Configuration

```yaml
endpoints:
  - name: "endpoint_name"
    url: "/api/endpoint"
    method: "GET"  # GET, POST, PUT, DELETE, PATCH
    headers:
      Accept: "application/json"
      User-Agent: "DataScraper/1.0"
    params:
      limit: 100
      offset: 0
    body:  # For POST/PUT requests
      key: "value"
    timeout: 30
    retry_attempts: 3
    data_path: "$.data.items"  # JSON path to extract data
```

### Data Transformation

#### Field Mapping
```yaml
transformation:
  field_mapping:
    source_field: "target_field"
    nested.field: "flattened_field"
    "array.0.item": "first_item"
```

#### Field Filtering
```yaml
transformation:
  field_filters:
    string_field:
      type: "string"
      lowercase: true
      strip: true
    number_field:
      type: "number"
      min: 0
      max: 100
    date_field:
      type: "date"
      format: "%Y-%m-%d"
```

#### Data Validation
```yaml
transformation:
  data_validation:
    required_field:
      required: true
      type: "string"
      min_length: 1
    email_field:
      type: "string"
      pattern: "^[^@]+@[^@]+\\.[^@]+$"
```

### Rate Limiting

```yaml
rate_limit:
  requests_per_minute: 60
  requests_per_hour: 1000
  delay_between_requests: 1.0  # seconds
```

### Output Configuration

```yaml
output_config:
  format: "json"  # json, csv
  filename: "my_data"
```

## Command Line Interface

### Scrape Command
```bash
# Basic scraping
python -m agent.main scrape --config my-api

# With job ID
python -m agent.main scrape --config my-api --job-id my-job-123

# With configuration overrides
python -m agent.main scrape --config my-api --override '{"rate_limit": {"requests_per_minute": 30}}'
```

### List Command
```bash
# List configurations in table format
python -m agent.main list

# List in JSON format
python -m agent.main list --format json

# List in simple format
python -m agent.main list --format simple
```

### Validate Command
```bash
# Validate configuration
python -m agent.main validate --config my-api
```

### Info Command
```bash
# Get detailed configuration information
python -m agent.main info --config my-api
```

## Docker Deployment

### Build Image
```bash
docker build -t data-scraper .
```

### Run Container
```bash
# Mount configuration and output directories
docker run -v $(pwd)/config:/app/config \
           -v $(pwd)/output:/app/output \
           -e API_TOKEN=your-token \
           data-scraper scrape --config my-api
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: data-scraper
spec:
  replicas: 1
  selector:
    matchLabels:
      app: data-scraper
  template:
    metadata:
      labels:
        app: data-scraper
    spec:
      containers:
      - name: data-scraper
        image: data-scraper:latest
        env:
        - name: API_TOKEN
          valueFrom:
            secretKeyRef:
              name: api-secrets
              key: token
        volumeMounts:
        - name: config
          mountPath: /app/config
        - name: output
          mountPath: /app/output
      volumes:
      - name: config
        configMap:
          name: api-configs
      - name: output
        persistentVolumeClaim:
          claimName: data-pvc
```

## Examples

### GitHub API Scraper
See `examples/config/apis/github-api.yaml` for a complete GitHub API configuration.

### Weather API Scraper
See `examples/config/apis/weather-api.yaml` for a weather API configuration.

## Environment Variables

- `API_TOKEN`: Bearer token for API authentication
- `API_KEY`: API key for key-based authentication
- `API_USERNAME`: Username for basic authentication
- `API_PASSWORD`: Password for basic authentication
- `VERBOSE`: Set to "true" for debug logging

## Output

The scraper generates output files in the configured output directory:

- **JSON Format**: Structured JSON with all scraped data
- **CSV Format**: Flattened CSV with endpoint and timestamp columns

## Logging

Logs are written to:
- Console (stdout)
- File: `/app/logs/data_scraper.log`

Log levels:
- INFO: General execution information
- WARNING: Non-critical issues
- ERROR: Errors that don't stop execution
- DEBUG: Detailed debugging information (when VERBOSE=true)

## Error Handling

The scraper handles various error scenarios:

- **Rate Limit Exceeded**: Automatically waits and retries
- **Network Errors**: Retries with exponential backoff
- **Authentication Errors**: Logs and continues with next endpoint
- **Data Validation Errors**: Logs warnings and continues processing

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.


