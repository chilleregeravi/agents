"""
Data input utilities for separated research workflow.

This module provides utilities for accepting research data from various sources:
- Manual input
- File uploads
- API integrations
- Database queries
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..models.research_config import ResearchData

logger = logging.getLogger(__name__)


class DataInputError(Exception):
    """Exception raised when data input processing fails."""

    pass


class ResearchDataInput:
    """
    Utility class for handling research data input from various sources.
    """

    @staticmethod
    def from_manual_input(
        topic_name: str,
        content_items: List[Dict[str, Any]],
        collection_method: str = "manual_input",
        collection_notes: Optional[str] = None,
    ) -> ResearchData:
        """
        Create ResearchData from manual input.

        Args:
            topic_name: Name of the research topic
            content_items: List of content items with structure:
                {
                    "title": "Content title",
                    "content": "Content text",
                    "url": "Source URL (optional)",
                    "source_type": "web_pages|documents|news_articles|social_media",
                    "publication_date": "2024-01-15T00:00:00Z (optional)"
                }
            collection_method: Method used to collect the data
            collection_notes: Notes about the collection process

        Returns:
            ResearchData object
        """
        try:
            # Organize content by type
            content_by_type = {
                "web_pages": [],
                "documents": [],
                "news_articles": [],
                "social_media": [],
            }

            total_content_length = 0
            data_sources = set()

            for item in content_items:
                content_type = item.get("source_type", "web_pages")
                if content_type not in content_by_type:
                    content_type = "web_pages"  # Default

                content_by_type[content_type].append(item)

                # Calculate content length
                content = item.get("content", "")
                total_content_length += len(content)

                # Add source URL if available
                if "url" in item:
                    data_sources.add(item["url"])

            # Calculate quality metrics
            source_diversity = min(1.0, len(data_sources) / 10.0)  # Normalize to 0-1
            content_freshness = 0.8  # Default for manual input
            relevance_score = 0.9  # Default for manual input

            return ResearchData(
                topic_name=topic_name,
                data_sources=list(data_sources),
                web_pages=content_by_type["web_pages"],
                documents=content_by_type["documents"],
                news_articles=content_by_type["news_articles"],
                social_media=content_by_type["social_media"],
                collection_method=collection_method,
                collection_notes=collection_notes,
                total_content_length=total_content_length,
                source_diversity=source_diversity,
                content_freshness=content_freshness,
                relevance_score=relevance_score,
            )

        except Exception as e:
            raise DataInputError(
                f"Failed to create ResearchData from manual input: {e}"
            )

    @staticmethod
    def from_json_file(file_path: Union[str, Path]) -> ResearchData:
        """
        Create ResearchData from JSON file.

        Args:
            file_path: Path to JSON file containing research data

        Returns:
            ResearchData object
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Validate required fields
            required_fields = ["topic_name", "data_sources"]
            for field in required_fields:
                if field not in data:
                    raise DataInputError(f"Missing required field: {field}")

            # Create ResearchData object
            return ResearchData(**data)

        except json.JSONDecodeError as e:
            raise DataInputError(f"Invalid JSON file: {e}")
        except Exception as e:
            raise DataInputError(f"Failed to load research data from file: {e}")

    @staticmethod
    def from_text_files(
        topic_name: str,
        file_paths: List[Union[str, Path]],
        collection_notes: Optional[str] = None,
    ) -> ResearchData:
        """
        Create ResearchData from multiple text files.

        Args:
            topic_name: Name of the research topic
            file_paths: List of paths to text files
            collection_notes: Notes about the collection process

        Returns:
            ResearchData object
        """
        try:
            content_items = []
            data_sources = []

            for file_path in file_paths:
                path = Path(file_path)
                if not path.exists():
                    logger.warning(f"File not found: {file_path}")
                    continue

                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()

                    content_items.append(
                        {
                            "title": path.stem,
                            "content": content,
                            "url": str(path),
                            "source_type": "documents",
                            "publication_date": (
                                datetime.fromtimestamp(path.stat().st_mtime).isoformat()
                            ),
                        }
                    )

                    data_sources.append(str(path))

                except Exception as e:
                    logger.error(f"Failed to read file {file_path}: {e}")

            if not content_items:
                raise DataInputError("No valid content found in provided files")

            return ResearchDataInput.from_manual_input(
                topic_name=topic_name,
                content_items=content_items,
                collection_method="file_upload",
                collection_notes=collection_notes,
            )

        except Exception as e:
            raise DataInputError(f"Failed to create ResearchData from text files: {e}")

    @staticmethod
    def from_api_response(
        topic_name: str,
        api_data: Dict[str, Any],
        collection_method: str = "api_integration",
        collection_notes: Optional[str] = None,
    ) -> ResearchData:
        """
        Create ResearchData from API response.

        Args:
            topic_name: Name of the research topic
            api_data: API response data
            collection_method: Method used to collect the data
            collection_notes: Notes about the collection process

        Returns:
            ResearchData object
        """
        try:
            # Extract content from API response
            content_items = []
            data_sources = []

            # Handle different API response formats
            if "articles" in api_data:
                for article in api_data["articles"]:
                    content_items.append(
                        {
                            "title": article.get("title", ""),
                            "content": article.get("content", ""),
                            "url": article.get("url", ""),
                            "source_type": "news_articles",
                            "publication_date": article.get("published_at"),
                        }
                    )
                    if article.get("url"):
                        data_sources.append(article["url"])

            elif "results" in api_data:
                for result in api_data["results"]:
                    content_items.append(
                        {
                            "title": result.get("title", ""),
                            "content": result.get("snippet", ""),
                            "url": result.get("url", ""),
                            "source_type": "web_pages",
                            "publication_date": result.get("date"),
                        }
                    )
                    if result.get("url"):
                        data_sources.append(result["url"])

            elif "data" in api_data:
                # Generic data format
                for item in api_data["data"]:
                    content_items.append(
                        {
                            "title": item.get("title", ""),
                            "content": item.get("content", ""),
                            "url": item.get("url", ""),
                            "source_type": item.get("type", "web_pages"),
                            "publication_date": item.get("date"),
                        }
                    )
                    if item.get("url"):
                        data_sources.append(item["url"])

            if not content_items:
                raise DataInputError("No valid content found in API response")

            return ResearchDataInput.from_manual_input(
                topic_name=topic_name,
                content_items=content_items,
                collection_method=collection_method,
                collection_notes=collection_notes,
            )

        except Exception as e:
            raise DataInputError(
                f"Failed to create ResearchData from API response: {e}"
            )

    @staticmethod
    def validate_research_data(research_data: ResearchData) -> List[str]:
        """
        Validate research data and return list of issues.

        Args:
            research_data: Research data to validate

        Returns:
            List of validation issues (empty if valid)
        """
        issues = []

        # Check required fields
        if not research_data.topic_name:
            issues.append("Topic name is required")

        if not research_data.collection_method:
            issues.append("Collection method is required")

        # Check content
        total_items = (
            len(research_data.web_pages)
            + len(research_data.documents)
            + len(research_data.news_articles)
            + len(research_data.social_media)
        )

        if total_items == 0:
            issues.append("No content items found")

        if research_data.total_content_length < 100:
            issues.append("Total content length is too short (< 100 characters)")

        # Check quality metrics
        if research_data.source_diversity < 0.0 or research_data.source_diversity > 1.0:
            issues.append("Source diversity must be between 0.0 and 1.0")

        if (
            research_data.content_freshness < 0.0
            or research_data.content_freshness > 1.0
        ):
            issues.append("Content freshness must be between 0.0 and 1.0")

        if research_data.relevance_score < 0.0 or research_data.relevance_score > 1.0:
            issues.append("Relevance score must be between 0.0 and 1.0")

        return issues

    @staticmethod
    def create_sample_data(topic_name: str = "Sample Research Topic") -> ResearchData:
        """
        Create sample research data for testing.

        Args:
            topic_name: Name of the sample research topic

        Returns:
            Sample ResearchData object
        """
        sample_content = [
            {
                "title": "Sample Article 1",
                "content": "This is a sample article about the research topic. "
                "It contains relevant information and insights that "
                "would be useful for analysis.",
                "url": "https://example.com/article1",
                "source_type": "news_articles",
                "publication_date": "2024-01-15T00:00:00Z",
            },
            {
                "title": "Sample Document 1",
                "content": "This is a sample document with detailed information "
                "about the research topic. It includes technical details "
                "and analysis that would be valuable for research.",
                "url": "https://example.com/document1",
                "source_type": "documents",
                "publication_date": "2024-01-10T00:00:00Z",
            },
            {
                "title": "Sample Web Page 1",
                "content": "This is a sample web page with general information "
                "about the research topic. It provides context and "
                "background information.",
                "url": "https://example.com/webpage1",
                "source_type": "web_pages",
                "publication_date": "2024-01-12T00:00:00Z",
            },
        ]

        return ResearchDataInput.from_manual_input(
            topic_name=topic_name,
            content_items=sample_content,
            collection_method="sample_data",
            collection_notes="Sample data created for testing purposes",
        )
