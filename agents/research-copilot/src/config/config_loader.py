"""
Simplified Research Configuration Loader.

This module provides functionality to load research configurations from
mounted ConfigMap files, eliminating the need for Kubernetes API client.
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from pydantic import ValidationError

from ..models.research_config import (
    MARKET_RESEARCH_TEMPLATE,
    TECH_RESEARCH_TEMPLATE,
    ResearchConfiguration,
)

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Exception raised when configuration loading fails."""

    pass


class ConfigLoader:
    """
    Simplified loader for research configurations from mounted files.

    This approach leverages Kubernetes' native ConfigMap mounting instead
    of using the Kubernetes API client at runtime.
    """

    def __init__(self, config_base_path: str = "/app/config"):
        """
        Initialize the configuration loader.

        Args:
            config_base_path: Base path where ConfigMaps are mounted
        """
        self.config_base_path = Path(config_base_path)
        self.templates_path = self.config_base_path / "templates"
        self.custom_path = self.config_base_path / "custom"

        # Built-in templates
        self._builtin_templates: Dict[str, ResearchConfiguration] = {
            "tech-research": TECH_RESEARCH_TEMPLATE,
            "market-research": MARKET_RESEARCH_TEMPLATE,
        }

        logger.info(
            f"Initialized config loader with base path: {self.config_base_path}"
        )

    def load_research_config(
        self, template_name: Optional[str] = None, raise_on_error: bool = True
    ) -> ResearchConfiguration:
        """
        Load a research configuration.

        Args:
            template_name: Name of the template to load. If None, uses RESEARCH_TEMPLATE env var
            raise_on_error: If True, raise errors instead of falling back to defaults

        Returns:
            ResearchConfiguration: Loaded and validated configuration

        Raises:
            ConfigurationError: If configuration loading or validation fails and raise_on_error is True
        """
        # Determine which template to use
        if template_name is None:
            template_name = os.getenv("RESEARCH_TEMPLATE", "tech-research")

        logger.info(f"Loading research configuration: {template_name}")

        # Try to load from mounted files first
        try:
            config = self._load_from_mounted_files(template_name)
            if config:
                return config
        except Exception as e:
            if raise_on_error and template_name not in self._builtin_templates:
                raise ConfigurationError(
                    f"Failed to load configuration '{template_name}': {e}"
                )
            logger.warning(f"Failed to load from mounted files: {e}")

        # Fall back to built-in templates
        if template_name in self._builtin_templates:
            logger.info(f"Using built-in template: {template_name}")
            return self._builtin_templates[template_name]

        # If raise_on_error is True and we can't find the template, raise error
        if raise_on_error:
            raise ConfigurationError(f"Template '{template_name}' not found")

        # Default to tech research if nothing else works
        logger.warning(
            f"Template '{template_name}' not found, using default tech-research"
        )
        return self._builtin_templates["tech-research"]

    def _load_from_mounted_files(
        self, template_name: str
    ) -> Optional[ResearchConfiguration]:
        """
        Load configuration from mounted ConfigMap files.

        Args:
            template_name: Name of the template directory

        Returns:
            ResearchConfiguration if found and valid, None otherwise
        """
        template_dir = self.templates_path / template_name
        custom_file = self.custom_path / f"{template_name}.yaml"

        # Try custom configuration first
        if custom_file.exists():
            logger.info(f"Loading custom configuration from: {custom_file}")
            return self._load_config_from_file(custom_file)

        # Try mounted template directory
        if template_dir.exists():
            research_file = template_dir / "research_prompt.yaml"
            schema_file = template_dir / "output_schema.yaml"

            if research_file.exists() and schema_file.exists():
                logger.info(f"Loading template from directory: {template_dir}")
                return self._load_config_from_files(research_file, schema_file)

        return None

    def _load_config_from_file(self, config_file: Path) -> ResearchConfiguration:
        """
        Load complete configuration from a single YAML file.

        Args:
            config_file: Path to the configuration file

        Returns:
            ResearchConfiguration: Loaded and validated configuration
        """
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            return ResearchConfiguration(**config_data)

        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in {config_file}: {e}")
        except ValidationError as e:
            raise ConfigurationError(f"Invalid configuration in {config_file}: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load {config_file}: {e}")

    def _load_config_from_files(
        self, research_file: Path, schema_file: Path
    ) -> ResearchConfiguration:
        """
        Load configuration from separate research and schema files.

        Args:
            research_file: Path to research prompt YAML
            schema_file: Path to output schema YAML

        Returns:
            ResearchConfiguration: Loaded and validated configuration
        """
        try:
            # Load research prompt
            with open(research_file, "r", encoding="utf-8") as f:
                research_data = yaml.safe_load(f)

            # Load output schema
            with open(schema_file, "r", encoding="utf-8") as f:
                schema_data = yaml.safe_load(f)

            # Combine into full configuration
            config_data = {
                "name": research_data.get("description", "Custom Research"),
                "description": research_data.get("description", ""),
                "version": "1.0",
                "research_request": research_data.get("research_request", {}),
                "output_schema": schema_data,
            }

            return ResearchConfiguration(**config_data)

        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML: {e}")
        except ValidationError as e:
            raise ConfigurationError(f"Invalid configuration: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}")

    def list_available_templates(self) -> List[str]:
        """
        List all available research templates.

        Returns:
            List of template names
        """
        templates = list(self._builtin_templates.keys())

        # Add mounted templates
        if self.templates_path.exists():
            for item in self.templates_path.iterdir():
                if item.is_dir() and (item / "research_prompt.yaml").exists():
                    templates.append(item.name)

        # Add custom configurations
        if self.custom_path.exists():
            for item in self.custom_path.glob("*.yaml"):
                templates.append(item.stem)

        return sorted(set(templates))

    def get_config_info(self, template_name: str) -> Dict[str, str]:
        """
        Get information about a specific template.

        Args:
            template_name: Name of the template

        Returns:
            Dictionary with template information
        """
        try:
            config = self.load_research_config(template_name, raise_on_error=False)
            # If we got a built-in template as fallback, detect it
            actual_source = self._get_template_source(template_name)
            if (
                actual_source == "unknown"
                and config.name == "Technology Research Template"
            ):
                actual_source = "builtin"

            return {
                "name": config.name,
                "description": config.description,
                "version": config.version,
                "source": actual_source,
            }
        except Exception as e:
            return {
                "name": template_name,
                "description": f"Error loading template: {e}",
                "version": "unknown",
                "source": "error",
            }

    def _get_template_source(self, template_name: str) -> str:
        """Get the source of a template (builtin, mounted, custom)."""
        custom_file = self.custom_path / f"{template_name}.yaml"
        template_dir = self.templates_path / template_name

        if custom_file.exists():
            return "custom"
        elif template_dir.exists():
            return "mounted"
        elif template_name in self._builtin_templates:
            return "builtin"
        else:
            return "unknown"


# Global instance
_config_loader: Optional[ConfigLoader] = None


def get_config_loader() -> ConfigLoader:
    """Get the global configuration loader instance."""
    global _config_loader
    if _config_loader is None:
        config_path = os.getenv("CONFIG_BASE_PATH", "/app/config")
        _config_loader = ConfigLoader(config_path)
    return _config_loader


def load_research_config(template_name: Optional[str] = None) -> ResearchConfiguration:
    """
    Convenience function to load a research configuration.

    Args:
        template_name: Name of the template to load

    Returns:
        ResearchConfiguration: Loaded configuration
    """
    return get_config_loader().load_research_config(template_name)
