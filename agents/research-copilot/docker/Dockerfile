# Multi-stage build for LLM Release Radar Agent
# Optimized for Raspberry Pi 5 ARM64 architecture

# Build stage
FROM python:3.11-slim-bookworm AS builder

# Set build arguments
ARG BUILDPLATFORM
ARG TARGETPLATFORM

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create build directory
WORKDIR /build

# Copy requirements first for better caching
COPY requirements/ requirements/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements/requirements.txt

# Production stage
FROM python:3.11-slim-bookworm AS production

# Set labels
LABEL maintainer="Agent Developer <dev@example.com>"
LABEL description="LLM Release Radar Agent for monitoring AI/ML news"
LABEL version="1.0.0"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1000 agent && \
    useradd --uid 1000 --gid agent --shell /bin/bash --create-home agent

# Create application directory
WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Copy application code
COPY src/ src/
COPY requirements/ requirements/

# Set ownership
RUN chown -R agent:agent /app

# Switch to non-root user
USER agent

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import asyncio; from src.agent.main import LLMReleaseRadarAgent; \
                   agent = LLMReleaseRadarAgent(); \
                   result = asyncio.run(agent.health_check()); \
                   exit(0 if result['agent'] == 'healthy' else 1)"

# Default command
CMD ["python", "-m", "src.agent.main"]
