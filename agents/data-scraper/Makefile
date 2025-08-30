# Data Scraper Agent Configuration
# This Makefile contains only agent-specific configuration
# All targets are inherited from the root Makefile

# Agent-specific configuration
AGENT_NAME := data-scraper
IMAGE_NAME := $(AGENT_NAME)
IMAGE_TAG := $(shell git rev-parse --short HEAD 2>/dev/null || echo "latest")
REGISTRY := localhost:5000

# Python configuration
PYTHON := python3
VENV := venv
REQUIREMENTS := requirements/requirements.txt
DEV_REQUIREMENTS := requirements/requirements-dev.txt

# Docker configuration
DOCKERFILE := docker/Dockerfile
DOCKER_CONTEXT := .

# Kubernetes configuration
K8S_NAMESPACE := data-scraper
K8S_BASE := k8s/base
K8S_OVERLAYS := k8s/overlays
ENVIRONMENT ?= production

# Export agent name for root Makefile
export AGENT := $(AGENT_NAME)

# Include the root Makefile for all targets
include ../../Makefile
