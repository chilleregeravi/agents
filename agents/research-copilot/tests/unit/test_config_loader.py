"""Unit tests for ConfigLoader."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from src.config.config_loader import (
    ConfigLoader,
    ConfigurationError,
    get_config_loader,
    load_research_config,
)
from src.models.research_config import ResearchConfiguration


class TestConfigLoader:
    """Test ConfigLoader class."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary directory for test configs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def sample_research_yaml(self):
        """Sample research configuration YAML."""
        return """
        description: "Test research configuration"
        research_request:
          topic:
            name: "Test Topic"
            description: "Test description"
            keywords: ["test", "sample"]
            focus_areas: ["testing"]
            time_range: "past_week"
            depth: "detailed"
            exclude_terms: []
          search_strategy:
            max_sources: 10
            source_types: ["news"]
            credibility_threshold: 0.8
            max_search_depth: 2
            parallel_searches: 3
            enable_follow_up: true
            language_preference: ["en"]
          analysis_instructions: "Test analysis instructions"
          priority: 5
        """

    @pytest.fixture
    def sample_schema_yaml(self):
        """Sample output schema YAML."""
        return """
        output_format: "notion_page"
        template: "research_report"
        page_structure:
          title_template: "Test Report - {topic_name}"
          tags: ["test"]
          sections:
            - name: "Summary"
              type: "text_block"
              content_source: "summary"
              order: 1
              required: true
              configuration:
                max_length: 200
        content_processing:
          summary_length: "short"
          include_confidence_scores: false
        """

    def test_init_default_path(self):
        """Test initialization with default config path."""
        loader = ConfigLoader()

        assert loader.config_base_path == Path("/app/config")
        assert loader.templates_path == Path("/app/config/templates")
        assert loader.custom_path == Path("/app/config/custom")
        assert "tech-research" in loader._builtin_templates
        assert "market-research" in loader._builtin_templates

    def test_init_custom_path(self, temp_config_dir):
        """Test initialization with custom config path."""
        loader = ConfigLoader(temp_config_dir)

        assert loader.config_base_path == Path(temp_config_dir)
        assert loader.templates_path == Path(temp_config_dir) / "templates"
        assert loader.custom_path == Path(temp_config_dir) / "custom"

    def test_load_builtin_template(self, temp_config_dir):
        """Test loading built-in template."""
        loader = ConfigLoader(temp_config_dir)

        config = loader.load_research_config("tech-research")

        assert isinstance(config, ResearchConfiguration)
        assert config.name == "Technology Research Template"

    def test_load_nonexistent_template_fallback(self, temp_config_dir):
        """Test loading nonexistent template falls back to default."""
        loader = ConfigLoader(temp_config_dir)

        config = loader.load_research_config(
            "nonexistent-template", raise_on_error=False
        )

        assert isinstance(config, ResearchConfiguration)
        assert config.name == "Technology Research Template"  # Default fallback

    def test_load_from_custom_file(
        self, temp_config_dir, sample_research_yaml, sample_schema_yaml
    ):
        """Test loading from custom configuration file."""
        # Create custom config directory and file
        custom_dir = Path(temp_config_dir) / "custom"
        custom_dir.mkdir(parents=True, exist_ok=True)

        custom_file = custom_dir / "custom-research.yaml"

        # Create a complete configuration
        complete_config = """
        name: "Custom Research"
        description: "Custom research configuration"
        version: "1.0"
        research_request:
          topic:
            name: "Custom Topic"
            description: "Custom description"
            keywords: ["custom", "test"]
            focus_areas: ["testing"]
            time_range: "past_week"
            depth: "detailed"
            exclude_terms: []
          search_strategy:
            max_sources: 5
            source_types: ["news"]
            credibility_threshold: 0.9
            max_search_depth: 1
            parallel_searches: 2
            enable_follow_up: false
            language_preference: ["en"]
          analysis_instructions: "Custom analysis"
          priority: 9
        output_schema:
          output_format: "notion_page"
          template: "custom_report"
          page_structure:
            title_template: "Custom Report"
            tags: ["custom"]
            sections:
              - name: "Results"
                type: "text_block"
                content_source: "results"
                order: 1
                required: true
                configuration:
                  max_length: 300
          content_processing:
            summary_length: "detailed"
            include_confidence_scores: true
        """

        with open(custom_file, "w") as f:
            f.write(complete_config)

        loader = ConfigLoader(temp_config_dir)
        config = loader.load_research_config("custom-research")

        assert config.name == "Custom Research"
        assert config.research_request.topic.name == "Custom Topic"
        assert config.research_request.search_strategy.max_sources == 5

    def test_load_from_template_directory(
        self, temp_config_dir, sample_research_yaml, sample_schema_yaml
    ):
        """Test loading from template directory with separate files."""
        # Create template directory
        template_dir = Path(temp_config_dir) / "templates" / "test-template"
        template_dir.mkdir(parents=True, exist_ok=True)

        # Create research and schema files
        research_file = template_dir / "research_prompt.yaml"
        schema_file = template_dir / "output_schema.yaml"

        with open(research_file, "w") as f:
            f.write(sample_research_yaml)

        with open(schema_file, "w") as f:
            f.write(sample_schema_yaml)

        loader = ConfigLoader(temp_config_dir)
        config = loader.load_research_config("test-template")

        assert isinstance(config, ResearchConfiguration)
        assert config.research_request.topic.name == "Test Topic"

    def test_invalid_yaml_error(self, temp_config_dir):
        """Test error handling for invalid YAML."""
        custom_dir = Path(temp_config_dir) / "custom"
        custom_dir.mkdir(parents=True, exist_ok=True)

        custom_file = custom_dir / "invalid.yaml"
        with open(custom_file, "w") as f:
            f.write("invalid: yaml: content: [")

        loader = ConfigLoader(temp_config_dir)

        with pytest.raises(ConfigurationError, match="Failed to load configuration"):
            loader.load_research_config("invalid", raise_on_error=True)

    def test_invalid_config_error(self, temp_config_dir):
        """Test error handling for invalid configuration."""
        custom_dir = Path(temp_config_dir) / "custom"
        custom_dir.mkdir(parents=True, exist_ok=True)

        custom_file = custom_dir / "invalid-config.yaml"
        with open(custom_file, "w") as f:
            f.write(
                """
            name: "Invalid Config"
            # Missing required fields
            """
            )

        loader = ConfigLoader(temp_config_dir)

        with pytest.raises(ConfigurationError, match="Failed to load configuration"):
            loader.load_research_config("invalid-config", raise_on_error=True)

    def test_list_available_templates(self, temp_config_dir):
        """Test listing available templates."""
        # Create some template directories
        templates_dir = Path(temp_config_dir) / "templates"
        templates_dir.mkdir(parents=True, exist_ok=True)

        template1_dir = templates_dir / "template1"
        template1_dir.mkdir()
        (template1_dir / "research_prompt.yaml").touch()

        template2_dir = templates_dir / "template2"
        template2_dir.mkdir()
        (template2_dir / "research_prompt.yaml").touch()

        # Create custom config
        custom_dir = Path(temp_config_dir) / "custom"
        custom_dir.mkdir(parents=True, exist_ok=True)
        (custom_dir / "custom1.yaml").touch()

        loader = ConfigLoader(temp_config_dir)
        templates = loader.list_available_templates()

        # Should include built-in templates, mounted templates, and custom configs
        assert "tech-research" in templates
        assert "market-research" in templates
        assert "template1" in templates
        assert "template2" in templates
        assert "custom1" in templates

    def test_get_config_info(self, temp_config_dir):
        """Test getting configuration information."""
        loader = ConfigLoader(temp_config_dir)

        info = loader.get_config_info("tech-research")

        assert info["name"] == "Technology Research Template"
        assert info["source"] == "builtin"
        assert "version" in info

    def test_get_config_info_error(self, temp_config_dir):
        """Test getting info for invalid configuration."""
        loader = ConfigLoader(temp_config_dir)

        info = loader.get_config_info("nonexistent")

        # Should fall back to built-in template since raise_on_error=False
        assert info["name"] == "Technology Research Template"
        assert info["source"] == "builtin"

    @patch.dict(os.environ, {"RESEARCH_TEMPLATE": "custom-template"})
    def test_load_with_env_var(self, temp_config_dir):
        """Test loading template specified by environment variable."""
        loader = ConfigLoader(temp_config_dir)

        # Should fall back to default since custom-template doesn't exist
        config = loader.load_research_config(raise_on_error=False)

        assert isinstance(config, ResearchConfiguration)


class TestGlobalFunctions:
    """Test global configuration functions."""

    @patch("src.config.config_loader.ConfigLoader")
    def test_get_config_loader_singleton(self, mock_loader_class):
        """Test that get_config_loader returns singleton instance."""
        mock_instance = MagicMock()
        mock_loader_class.return_value = mock_instance

        # First call should create instance
        loader1 = get_config_loader()
        assert loader1 == mock_instance
        assert mock_loader_class.call_count == 1

        # Second call should return same instance
        loader2 = get_config_loader()
        assert loader2 == mock_instance
        assert mock_loader_class.call_count == 1  # Should not create new instance

    @patch.dict(os.environ, {"CONFIG_BASE_PATH": "/custom/path"})
    @patch("src.config.config_loader.ConfigLoader")
    def test_get_config_loader_custom_path(self, mock_loader_class):
        """Test get_config_loader with custom path from environment."""
        # Reset the global variable to ensure fresh initialization
        import src.config.config_loader

        src.config.config_loader._config_loader = None

        mock_instance = MagicMock()
        mock_loader_class.return_value = mock_instance

        get_config_loader()

        mock_loader_class.assert_called_once_with("/custom/path")

    @patch("src.config.config_loader.get_config_loader")
    def test_load_research_config_function(self, mock_get_loader):
        """Test convenience function for loading research config."""
        mock_loader = MagicMock()
        mock_config = MagicMock()
        mock_loader.load_research_config.return_value = mock_config
        mock_get_loader.return_value = mock_loader

        result = load_research_config("test-template")

        assert result == mock_config
        mock_loader.load_research_config.assert_called_once_with("test-template")


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary directory for test configs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    def test_file_not_found_fallback(self, temp_config_dir):
        """Test fallback when files are not found."""
        loader = ConfigLoader(temp_config_dir)

        # Should fall back to built-in template
        config = loader.load_research_config("nonexistent", raise_on_error=False)
        assert isinstance(config, ResearchConfiguration)

    @patch("builtins.open", side_effect=PermissionError("Permission denied"))
    def test_permission_error_fallback(self, mock_open, temp_config_dir):
        """Test fallback when file permissions are denied."""
        # Create the directory structure so the file appears to exist
        custom_dir = Path(temp_config_dir) / "custom"
        custom_dir.mkdir(parents=True, exist_ok=True)
        (custom_dir / "test.yaml").touch()

        loader = ConfigLoader(temp_config_dir)

        # Should fall back to built-in template due to permission error
        config = loader.load_research_config("test", raise_on_error=False)
        assert isinstance(config, ResearchConfiguration)

    def test_directory_creation_handling(self):
        """Test handling when directories don't exist."""
        # Use a non-existent path
        loader = ConfigLoader("/nonexistent/path")

        # Should still work and fall back to built-in templates
        templates = loader.list_available_templates()
        assert "tech-research" in templates
        assert "market-research" in templates
