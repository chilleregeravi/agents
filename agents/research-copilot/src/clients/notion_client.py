"""
Dynamic Notion Client with Schema-based Rendering.

This module provides a flexible Notion client that can create pages and content
based on configurable output schemas, supporting various content types and
formatting options.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import aiohttp
from notion_client import AsyncClient
from notion_client.errors import APIResponseError

from ..models.research_config import (
    AnalysisInsight,
    OutputSchema,
    PageSection,
    PageStructure,
    SearchResult,
    SectionConfiguration,
    SectionType,
)

logger = logging.getLogger(__name__)


class NotionClientError(Exception):
    """Exception raised for Notion client errors."""

    pass


class NotionClient:
    """
    Dynamic Notion client that creates pages based on configurable schemas.

    Supports various content types including text blocks, lists, tables,
    toggle blocks, callouts, and more. Renders content dynamically based
    on the provided output schema configuration.
    """

    def __init__(
        self,
        notion_token: str,
        database_id: Optional[str] = None,
        timeout: int = 30,
    ):
        """
        Initialize the dynamic Notion client.

        Args:
            notion_token: Notion integration token
            database_id: Default database ID for page creation
            timeout: Request timeout in seconds
        """
        self.client = AsyncClient(auth=notion_token)
        self.database_id = database_id
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None

        # Content type handlers
        self._content_handlers = {
            SectionType.TEXT_BLOCK: self._create_text_block,
            SectionType.BULLET_LIST: self._create_bullet_list,
            SectionType.NUMBERED_LIST: self._create_numbered_list,
            SectionType.TABLE: self._create_table,
            SectionType.TOGGLE_BLOCKS: self._create_toggle_blocks,
            SectionType.CALLOUT: self._create_callout,
            SectionType.QUOTE: self._create_quote,
            SectionType.CODE_BLOCK: self._create_code_block,
            SectionType.DIVIDER: self._create_divider,
        }

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def create_research_page(
        self,
        output_schema: OutputSchema,
        research_data: Dict[str, Any],
        database_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a research page based on the output schema and data.

        Args:
            output_schema: Output schema configuration
            research_data: Research data to populate the page
            database_id: Database ID (uses default if not provided)

        Returns:
            Created page information

        Raises:
            NotionClientError: If page creation fails
        """
        try:
            # Use provided database_id or fallback to default
            target_db_id = database_id or self.database_id
            if not target_db_id:
                raise NotionClientError("No database ID provided")

            # Generate page title
            title = self._generate_page_title(
                output_schema.page_structure.title_template, research_data
            )

            # Create the page
            page_data = {
                "parent": {"database_id": target_db_id},
                "properties": {"title": {"title": [{"text": {"content": title}}]}},
            }

            # Add tags if specified
            if output_schema.page_structure.tags:
                page_data["properties"]["Tags"] = {
                    "multi_select": [
                        {"name": tag} for tag in output_schema.page_structure.tags
                    ]
                }

            # Create the page
            page = await self.client.pages.create(**page_data)
            page_id = page["id"]

            logger.info(f"Created Notion page: {title} (ID: {page_id})")

            # Add content sections
            await self._add_page_content(
                page_id, output_schema.page_structure, research_data
            )

            return {
                "page_id": page_id,
                "url": page["url"],
                "title": title,
                "created_at": page["created_time"],
            }

        except APIResponseError as e:
            raise NotionClientError(f"Notion API error: {e}")
        except Exception as e:
            raise NotionClientError(f"Failed to create research page: {e}")

    def _generate_page_title(
        self, title_template: str, research_data: Dict[str, Any]
    ) -> str:
        """Generate page title from template and data."""
        # Get topic name from research data
        topic_name = research_data.get("topic", {}).get("name", "Research")

        # Format template with available data
        format_data = {
            "topic_name": topic_name,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M"),
            **research_data.get("metadata", {}),
        }

        try:
            return title_template.format(**format_data)
        except KeyError as e:
            logger.warning(f"Missing template variable {e}, using fallback title")
            return f"Research Report - {topic_name} - {format_data['date']}"

    async def _add_page_content(
        self,
        page_id: str,
        page_structure: PageStructure,
        research_data: Dict[str, Any],
    ) -> None:
        """Add content sections to the page."""
        # Sort sections by order
        sorted_sections = sorted(page_structure.sections, key=lambda s: s.order)

        blocks = []

        # Add header content if specified
        if page_structure.header_content:
            blocks.extend(self._create_text_block(page_structure.header_content, {}))

        # Process each section
        for section in sorted_sections:
            if not section.required and section.content_source not in research_data:
                logger.info(f"Skipping optional section: {section.name}")
                continue

            # Get content data for this section
            content_data = research_data.get(section.content_source, {})

            # Create section header
            blocks.append(
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {"rich_text": [{"text": {"content": section.name}}]},
                }
            )

            # Create section content
            section_blocks = await self._create_section_content(
                section, content_data, research_data
            )
            blocks.extend(section_blocks)

            # Add spacing between sections
            blocks.append(
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": []},
                }
            )

        # Add footer content if specified
        if page_structure.footer_content:
            blocks.extend(self._create_text_block(page_structure.footer_content, {}))

        # Add blocks to page in batches (Notion has a limit of 100 blocks per request)
        batch_size = 100
        for i in range(0, len(blocks), batch_size):
            batch = blocks[i : i + batch_size]
            await self.client.blocks.children.append(block_id=page_id, children=batch)

            logger.debug(f"Added batch of {len(batch)} blocks to page")

    async def _create_section_content(
        self,
        section: PageSection,
        content_data: Any,
        full_research_data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Create content blocks for a section."""
        handler = self._content_handlers.get(section.type)
        if not handler:
            logger.warning(f"No handler for section type: {section.type}")
            return self._create_text_block(
                f"Unsupported section type: {section.type}",
                section.configuration,
            )

        try:
            return await handler(
                content_data, section.configuration, full_research_data
            )
        except Exception as e:
            logger.error(f"Error creating section content: {e}")
            return self._create_text_block(
                f"Error rendering section: {str(e)}", section.configuration
            )

    def _create_text_block(
        self,
        content: Union[str, Dict, List],
        config: SectionConfiguration,
        full_data: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Create text block content."""
        if isinstance(content, dict):
            text = content.get("text", str(content))
        elif isinstance(content, list):
            text = "\n".join(str(item) for item in content)
        else:
            text = str(content)

        # Apply max length if specified
        if config.max_length and len(text) > config.max_length:
            text = text[: config.max_length] + "..."

        # Split into paragraphs
        paragraphs = text.split("\n\n")
        blocks = []

        for paragraph in paragraphs:
            if paragraph.strip():
                # Highlight key points if enabled
                if config.highlight_key_points and any(
                    keyword in paragraph.lower()
                    for keyword in [
                        "key",
                        "important",
                        "critical",
                        "significant",
                    ]
                ):
                    blocks.append(
                        {
                            "object": "block",
                            "type": "callout",
                            "callout": {
                                "rich_text": [{"text": {"content": paragraph.strip()}}],
                                "icon": {"emoji": "💡"},
                            },
                        }
                    )
                else:
                    blocks.append(
                        {
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [{"text": {"content": paragraph.strip()}}]
                            },
                        }
                    )

        return blocks

    async def _create_bullet_list(
        self,
        content: Union[List, Dict],
        config: SectionConfiguration,
        full_data: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Create bullet list content."""
        items = []

        if isinstance(content, dict):
            if "items" in content:
                items = content["items"]
            elif "findings" in content:
                items = content["findings"]
            else:
                items = [f"{k}: {v}" for k, v in content.items()]
        elif isinstance(content, list):
            items = content
        else:
            items = [str(content)]

        # Apply max items limit
        if config.max_items:
            items = items[: config.max_items]

        # Sort by impact if enabled
        if config.prioritize_by_impact and isinstance(items[0], dict):
            items = sorted(items, key=lambda x: x.get("impact_level", 0), reverse=True)

        blocks = []
        for item in items:
            if isinstance(item, dict):
                text = item.get("text", item.get("title", str(item)))

                # Add confidence score if enabled
                if config.include_confidence_scores and "confidence" in item:
                    text += f" (Confidence: {item['confidence']:.2f})"

                # Add source if enabled
                if config.include_sources and "source" in item:
                    text += f" - Source: {item['source']}"

            else:
                text = str(item)

            blocks.append(
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {"rich_text": [{"text": {"content": text}}]},
                }
            )

        return blocks

    async def _create_numbered_list(
        self,
        content: Union[List, Dict],
        config: SectionConfiguration,
        full_data: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Create numbered list content."""
        # Similar to bullet list but with numbered items
        bullet_blocks = await self._create_bullet_list(content, config, full_data)

        # Convert to numbered list
        numbered_blocks = []
        for block in bullet_blocks:
            numbered_block = block.copy()
            numbered_block["type"] = "numbered_list_item"
            numbered_block["numbered_list_item"] = numbered_block.pop(
                "bulleted_list_item"
            )
            numbered_blocks.append(numbered_block)

        return numbered_blocks

    async def _create_table(
        self,
        content: Union[List, Dict],
        config: SectionConfiguration,
        full_data: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Create table content."""
        if not config.columns:
            return self._create_text_block(
                "Table configuration missing columns", config
            )

        # Prepare table data
        rows = []

        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    row = []
                    for col in config.columns:
                        value = item.get(col.lower().replace(" ", "_"), "")

                        # Format numbers if enabled
                        if config.format_numbers and isinstance(value, (int, float)):
                            value = (
                                f"{value:,.2f}"
                                if isinstance(value, float)
                                else f"{value:,}"
                            )

                        row.append(str(value))
                    rows.append(row)
                else:
                    # Simple list item
                    row = [str(item)] + [""] * (len(config.columns) - 1)
                    rows.append(row)

        elif isinstance(content, dict):
            if "rows" in content:
                rows = content["rows"]
            else:
                # Convert dict to table rows
                for key, value in content.items():
                    row = [str(key), str(value)] + [""] * (len(config.columns) - 2)
                    rows.append(row)

        # Sort if specified
        if config.sort_by and rows:
            try:
                sort_index = config.columns.index(config.sort_by)

                # Try to sort numerically first, then fall back to string sorting
                def sort_key(x):
                    if sort_index >= len(x):
                        return (
                            0
                            if config.sort_by.lower()
                            in ["credibility", "score", "rating"]
                            else ""
                        )
                    val = x[sort_index]
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        return val

                # Sort in descending order for numeric fields like credibility, score, rating
                reverse_sort = config.sort_by.lower() in [
                    "credibility",
                    "score",
                    "rating",
                    "date",
                ]
                rows.sort(key=sort_key, reverse=reverse_sort)
            except ValueError:
                logger.warning(f"Sort column '{config.sort_by}' not found in columns")

        # Create table block
        table_rows = []

        # Header row
        header_cells = []
        for col in config.columns:
            header_cells.append(
                {
                    "rich_text": [
                        {
                            "text": {
                                "content": col,
                                "annotations": {"bold": True},
                            }
                        }
                    ]
                }
            )
        table_rows.append({"cells": header_cells})

        # Data rows
        for row in rows:
            cells = []
            for cell_value in row:
                cells.append({"rich_text": [{"text": {"content": str(cell_value)}}]})
            table_rows.append({"cells": cells})

        return [
            {
                "object": "block",
                "type": "table",
                "table": {
                    "table_width": len(config.columns),
                    "has_column_header": True,
                    "has_row_header": False,
                    "children": table_rows,
                },
            }
        ]

    async def _create_toggle_blocks(
        self,
        content: Union[List, Dict],
        config: SectionConfiguration,
        full_data: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Create toggle blocks content."""
        blocks = []

        if isinstance(content, dict):
            # Group by category if specified
            if config.group_by and config.group_by in content:
                grouped_content = content[config.group_by]
            else:
                grouped_content = content

            for key, value in grouped_content.items():
                toggle_content = []

                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        text = f"{sub_key}: {sub_value}"
                        toggle_content.append(
                            {
                                "object": "block",
                                "type": "paragraph",
                                "paragraph": {
                                    "rich_text": [{"text": {"content": text}}]
                                },
                            }
                        )
                elif isinstance(value, list):
                    for item in value:
                        toggle_content.append(
                            {
                                "object": "block",
                                "type": "bulleted_list_item",
                                "bulleted_list_item": {
                                    "rich_text": [{"text": {"content": str(item)}}]
                                },
                            }
                        )
                else:
                    toggle_content.append(
                        {
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [{"text": {"content": str(value)}}]
                            },
                        }
                    )

                blocks.append(
                    {
                        "object": "block",
                        "type": "toggle",
                        "toggle": {
                            "rich_text": [{"text": {"content": str(key)}}],
                            "children": toggle_content,
                        },
                    }
                )

        elif isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and "title" in item and "content" in item:
                    toggle_content = [
                        {
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [
                                    {"text": {"content": str(item["content"])}}
                                ]
                            },
                        }
                    ]

                    blocks.append(
                        {
                            "object": "block",
                            "type": "toggle",
                            "toggle": {
                                "rich_text": [{"text": {"content": item["title"]}}],
                                "children": toggle_content,
                            },
                        }
                    )

        return blocks

    def _create_callout(
        self,
        content: Union[str, Dict],
        config: SectionConfiguration,
        full_data: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Create callout content."""
        if isinstance(content, dict):
            text = content.get("text", str(content))
            icon = content.get("icon", "💡")
        else:
            text = str(content)
            icon = "💡"

        return [
            {
                "object": "block",
                "type": "callout",
                "callout": {
                    "rich_text": [{"text": {"content": text}}],
                    "icon": {"emoji": icon},
                },
            }
        ]

    def _create_quote(
        self,
        content: Union[str, Dict],
        config: SectionConfiguration,
        full_data: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Create quote content."""
        if isinstance(content, dict):
            text = content.get("text", str(content))
        else:
            text = str(content)

        return [
            {
                "object": "block",
                "type": "quote",
                "quote": {"rich_text": [{"text": {"content": text}}]},
            }
        ]

    def _create_code_block(
        self,
        content: Union[str, Dict],
        config: SectionConfiguration,
        full_data: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Create code block content."""
        if isinstance(content, dict):
            text = content.get("code", content.get("text", str(content)))
            language = content.get("language", "plain text")
        else:
            text = str(content)
            language = "plain text"

        return [
            {
                "object": "block",
                "type": "code",
                "code": {
                    "rich_text": [{"text": {"content": text}}],
                    "language": language,
                },
            }
        ]

    def _create_divider(
        self,
        content: Any,
        config: SectionConfiguration,
        full_data: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Create divider content."""
        return [{"object": "block", "type": "divider", "divider": {}}]

    async def update_page_properties(
        self, page_id: str, properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update page properties.

        Args:
            page_id: Page ID to update
            properties: Properties to update

        Returns:
            Updated page information
        """
        try:
            return await self.client.pages.update(
                page_id=page_id, properties=properties
            )
        except APIResponseError as e:
            raise NotionClientError(f"Failed to update page properties: {e}")

    async def add_comment(self, page_id: str, comment: str) -> Dict[str, Any]:
        """
        Add a comment to a page.

        Args:
            page_id: Page ID to comment on
            comment: Comment text

        Returns:
            Comment information
        """
        try:
            return await self.client.comments.create(
                parent={"page_id": page_id},
                rich_text=[{"text": {"content": comment}}],
            )
        except APIResponseError as e:
            raise NotionClientError(f"Failed to add comment: {e}")

    async def get_page_info(self, page_id: str) -> Dict[str, Any]:
        """
        Get page information.

        Args:
            page_id: Page ID to retrieve

        Returns:
            Page information
        """
        try:
            return await self.client.pages.retrieve(page_id=page_id)
        except APIResponseError as e:
            raise NotionClientError(f"Failed to retrieve page: {e}")


# Utility functions
def format_research_data_for_notion(
    search_results: List[SearchResult],
    insights: List[AnalysisInsight],
    metadata: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Format research data for Notion page creation.

    Args:
        search_results: List of search results
        insights: List of analysis insights
        metadata: Additional metadata

    Returns:
        Formatted data dictionary
    """
    return {
        "topic": metadata.get("topic", {}),
        "summary": {
            "text": metadata.get("summary", "Research summary not available"),
            "key_points": metadata.get("key_points", []),
        },
        "findings": [
            {
                "title": insight.title,
                "text": insight.content,
                "confidence": insight.confidence_score,
                "category": insight.category,
                "impact_level": insight.impact_level,
                "sources": insight.supporting_sources,
            }
            for insight in insights
        ],
        "analysis": {
            category: [
                insight
                for insight in insights
                if insight.category.lower() == category.lower()
            ]
            for category in set(insight.category for insight in insights)
        },
        "sources": [
            {
                "title": result.title,
                "url": result.url,
                "credibility": result.credibility_score,
                "date": result.publication_date.isoformat()
                if result.publication_date
                else "Unknown",
                "domain": result.domain,
                "relevance": result.relevance_score,
            }
            for result in search_results
        ],
        "metrics": metadata.get("metrics", {}),
        "competitors": metadata.get("competitors", {}),
        "insights": [
            {
                "title": insight.title,
                "content": insight.content,
                "confidence": insight.confidence_score,
                "impact_level": insight.impact_level,
            }
            for insight in insights
        ],
        "overview": metadata.get("overview", ""),
        "metadata": metadata,
    }
