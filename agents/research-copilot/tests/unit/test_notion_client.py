"""Unit tests for dynamic Notion client."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.clients.notion_client import (
    NotionClient,
    NotionClientError,
    format_research_data_for_notion,
)
from src.models.research_config import (
    AnalysisInsight,
    ContentProcessing,
    OutputFormat,
    OutputSchema,
    PageSection,
    PageStructure,
    SearchResult,
    SectionConfiguration,
    SectionType,
    SourceType,
)


class TestNotionClient:
    """Test NotionClient class."""

    @pytest.fixture
    def mock_notion_client(self):
        """Mock Notion client."""
        mock_client = AsyncMock()
        mock_page = {
            "id": "test-page-123",
            "url": "https://notion.so/test-page-123",
            "created_time": "2024-01-01T00:00:00.000Z",
            "properties": {},
        }
        mock_client.pages.create.return_value = mock_page
        mock_client.blocks.children.append.return_value = {"results": []}
        return mock_client

    @pytest.fixture
    def sample_output_schema(self):
        """Sample output schema."""
        sections = [
            PageSection(
                name="Executive Summary",
                type=SectionType.TEXT_BLOCK,
                content_source="summary",
                order=1,
                configuration=SectionConfiguration(
                    max_length=500, include_key_points=True
                ),
            ),
            PageSection(
                name="Key Findings",
                type=SectionType.BULLET_LIST,
                content_source="findings",
                order=2,
                configuration=SectionConfiguration(max_items=10, include_sources=True),
            ),
            PageSection(
                name="Sources",
                type=SectionType.TABLE,
                content_source="sources",
                order=3,
                configuration=SectionConfiguration(
                    columns=["Title", "URL", "Credibility", "Date"]
                ),
            ),
        ]

        page_structure = PageStructure(
            title_template="Research Report - {topic_name} - {date}",
            sections=sections,
            tags=["research", "analysis"],
        )

        return OutputSchema(
            output_format=OutputFormat.NOTION_PAGE,
            template="research_report",
            page_structure=page_structure,
            content_processing=ContentProcessing(),
        )

    @pytest.fixture
    def sample_research_data(self):
        """Sample research data."""
        return {
            "topic": {
                "name": "AI Research",
                "description": "Research on AI developments",
            },
            "summary": {
                "text": "This research explores recent AI developments...",
                "key_points": ["Point 1", "Point 2", "Point 3"],
            },
            "findings": [
                {
                    "title": "Finding 1",
                    "text": "Important discovery about AI",
                    "confidence": 0.9,
                    "source": "https://example.com/source1",
                },
                {
                    "title": "Finding 2",
                    "text": "Another significant finding",
                    "confidence": 0.8,
                    "source": "https://example.com/source2",
                },
            ],
            "sources": [
                {
                    "title": "AI Research Paper",
                    "url": "https://arxiv.org/paper1",
                    "credibility": 0.95,
                    "date": "2024-01-01",
                    "domain": "arxiv.org",
                },
                {
                    "title": "Tech News Article",
                    "url": "https://techcrunch.com/article1",
                    "credibility": 0.80,
                    "date": "2024-01-02",
                    "domain": "techcrunch.com",
                },
            ],
            "metadata": {
                "execution_id": "test-123",
                "config_name": "test-config",
            },
        }

    @patch("src.clients.notion_client.AsyncClient")
    def test_init(self, mock_client_class):
        """Test client initialization."""
        mock_client_class.return_value = AsyncMock()

        client = NotionClient(
            notion_token="test_token", database_id="test_db_id", timeout=60
        )

        assert client.database_id == "test_db_id"
        assert client.timeout == 60
        mock_client_class.assert_called_once_with(auth="test_token")

    @patch("src.clients.notion_client.AsyncClient")
    def test_init_without_database_id(self, mock_client_class):
        """Test initialization without database ID."""
        mock_client_class.return_value = AsyncMock()

        client = NotionClient(notion_token="test_token")

        assert client.database_id is None

    def test_generate_page_title(self, mock_notion_client, sample_research_data):
        """Test page title generation."""
        client = NotionClient("test_token")
        client.client = mock_notion_client

        title = client._generate_page_title(
            "Research Report - {topic_name} - {date}", sample_research_data
        )

        assert "AI Research" in title
        assert "Research Report" in title
        assert datetime.now().strftime("%Y-%m-%d") in title

    def test_generate_page_title_missing_variable(
        self, mock_notion_client, sample_research_data
    ):
        """Test page title generation with missing template variable."""
        client = NotionClient("test_token")
        client.client = mock_notion_client

        title = client._generate_page_title(
            "Report - {nonexistent_variable} - {topic_name}",
            sample_research_data,
        )

        # Should fall back to default format
        assert "AI Research" in title
        assert "Research Report" in title

    def test_create_text_block(self, mock_notion_client):
        """Test text block creation."""
        client = NotionClient("test_token")
        client.client = mock_notion_client

        config = SectionConfiguration(max_length=100)
        blocks = client._create_text_block("This is a test paragraph.", config)

        assert len(blocks) == 1
        assert blocks[0]["type"] == "paragraph"
        assert (
            blocks[0]["paragraph"]["rich_text"][0]["text"]["content"]
            == "This is a test paragraph."
        )

    def test_create_text_block_with_max_length(self, mock_notion_client):
        """Test text block creation with max length limit."""
        client = NotionClient("test_token")
        client.client = mock_notion_client

        long_text = "This is a very long text that exceeds the maximum length limit."
        config = SectionConfiguration(max_length=20)
        blocks = client._create_text_block(long_text, config)

        content = blocks[0]["paragraph"]["rich_text"][0]["text"]["content"]
        assert len(content) <= 23  # 20 + "..."
        assert content.endswith("...")

    def test_create_text_block_with_key_points(self, mock_notion_client):
        """Test text block creation with key points highlighting."""
        client = NotionClient("test_token")
        client.client = mock_notion_client

        text = "This is a key finding that is important for the research."
        config = SectionConfiguration(highlight_key_points=True)
        blocks = client._create_text_block(text, config)

        # Should create a callout for key points
        assert blocks[0]["type"] == "callout"
        assert blocks[0]["callout"]["icon"]["emoji"] == "💡"

    async def test_create_bullet_list(self, mock_notion_client):
        """Test bullet list creation."""
        client = NotionClient("test_token")
        client.client = mock_notion_client

        findings = [
            {"title": "Finding 1", "text": "First finding", "confidence": 0.9},
            {
                "title": "Finding 2",
                "text": "Second finding",
                "confidence": 0.8,
            },
        ]
        config = SectionConfiguration(include_confidence_scores=True)

        blocks = await client._create_bullet_list(findings, config)

        assert len(blocks) == 2
        for block in blocks:
            assert block["type"] == "bulleted_list_item"
            # Should include confidence scores
            content = block["bulleted_list_item"]["rich_text"][0]["text"]["content"]
            assert "Confidence:" in content

    async def test_create_bullet_list_with_max_items(self, mock_notion_client):
        """Test bullet list creation with max items limit."""
        client = NotionClient("test_token")
        client.client = mock_notion_client

        findings = [f"Finding {i}" for i in range(10)]
        config = SectionConfiguration(max_items=5)

        blocks = await client._create_bullet_list(findings, config)

        assert len(blocks) == 5

    async def test_create_numbered_list(self, mock_notion_client):
        """Test numbered list creation."""
        client = NotionClient("test_token")
        client.client = mock_notion_client

        items = ["Item 1", "Item 2", "Item 3"]
        config = SectionConfiguration()

        blocks = await client._create_numbered_list(items, config)

        assert len(blocks) == 3
        for block in blocks:
            assert block["type"] == "numbered_list_item"

    async def test_create_table(self, mock_notion_client):
        """Test table creation."""
        client = NotionClient("test_token")
        client.client = mock_notion_client

        sources = [
            {
                "title": "Source 1",
                "url": "https://example.com/1",
                "credibility": 0.9,
                "date": "2024-01-01",
            },
            {
                "title": "Source 2",
                "url": "https://example.com/2",
                "credibility": 0.8,
                "date": "2024-01-02",
            },
        ]
        config = SectionConfiguration(
            columns=["Title", "URL", "Credibility", "Date"],
            sort_by="credibility",
        )

        blocks = await client._create_table(sources, config)

        assert len(blocks) == 1
        table_block = blocks[0]
        assert table_block["type"] == "table"
        assert table_block["table"]["table_width"] == 4
        assert table_block["table"]["has_column_header"] is True

        # Check header row
        header_row = table_block["table"]["children"][0]
        assert len(header_row["cells"]) == 4
        assert header_row["cells"][0]["rich_text"][0]["text"]["content"] == "Title"

    async def test_create_table_with_sorting(self, mock_notion_client):
        """Test table creation with sorting."""
        client = NotionClient("test_token")
        client.client = mock_notion_client

        sources = [
            {"credibility": 0.7},
            {"credibility": 0.9},
            {"credibility": 0.8},
        ]
        config = SectionConfiguration(columns=["Credibility"], sort_by="Credibility")

        blocks = await client._create_table(sources, config)

        # Should be sorted by credibility (descending)
        table_block = blocks[0]
        data_rows = table_block["table"]["children"][1:]  # Skip header
        credibility_values = [
            float(row["cells"][0]["rich_text"][0]["text"]["content"])
            for row in data_rows
        ]
        assert credibility_values == sorted(credibility_values, reverse=True)

    async def test_create_toggle_blocks(self, mock_notion_client):
        """Test toggle blocks creation."""
        client = NotionClient("test_token")
        client.client = mock_notion_client

        analysis = {
            "Category 1": {
                "finding1": "First finding in category 1",
                "finding2": "Second finding in category 1",
            },
            "Category 2": ["Finding A", "Finding B"],
        }
        config = SectionConfiguration()

        blocks = await client._create_toggle_blocks(analysis, config)

        assert len(blocks) == 2
        for block in blocks:
            assert block["type"] == "toggle"
            assert "children" in block["toggle"]

    def test_create_callout(self, mock_notion_client):
        """Test callout creation."""
        client = NotionClient("test_token")
        client.client = mock_notion_client

        content = {"text": "Important information", "icon": "⚠️"}
        config = SectionConfiguration()

        blocks = client._create_callout(content, config)

        assert len(blocks) == 1
        assert blocks[0]["type"] == "callout"
        assert (
            blocks[0]["callout"]["rich_text"][0]["text"]["content"]
            == "Important information"
        )
        assert blocks[0]["callout"]["icon"]["emoji"] == "⚠️"

    def test_create_quote(self, mock_notion_client):
        """Test quote creation."""
        client = NotionClient("test_token")
        client.client = mock_notion_client

        content = "This is a quote from the research."
        config = SectionConfiguration()

        blocks = client._create_quote(content, config)

        assert len(blocks) == 1
        assert blocks[0]["type"] == "quote"
        assert blocks[0]["quote"]["rich_text"][0]["text"]["content"] == content

    def test_create_code_block(self, mock_notion_client):
        """Test code block creation."""
        client = NotionClient("test_token")
        client.client = mock_notion_client

        content = {"code": "print('Hello, World!')", "language": "python"}
        config = SectionConfiguration()

        blocks = client._create_code_block(content, config)

        assert len(blocks) == 1
        assert blocks[0]["type"] == "code"
        assert (
            blocks[0]["code"]["rich_text"][0]["text"]["content"]
            == "print('Hello, World!')"
        )
        assert blocks[0]["code"]["language"] == "python"

    def test_create_divider(self, mock_notion_client):
        """Test divider creation."""
        client = NotionClient("test_token")
        client.client = mock_notion_client

        blocks = client._create_divider(None, SectionConfiguration())

        assert len(blocks) == 1
        assert blocks[0]["type"] == "divider"

    async def test_create_research_page_success(
        self, mock_notion_client, sample_output_schema, sample_research_data
    ):
        """Test successful research page creation."""
        client = NotionClient("test_token", database_id="test_db")
        client.client = mock_notion_client

        result = await client.create_research_page(
            sample_output_schema, sample_research_data, database_id="custom_db"
        )

        assert result["page_id"] == "test-page-123"
        assert result["url"] == "https://notion.so/test-page-123"
        assert "AI Research" in result["title"]

        # Verify page creation was called
        mock_notion_client.pages.create.assert_called_once()
        create_args = mock_notion_client.pages.create.call_args[1]
        assert create_args["parent"]["database_id"] == "custom_db"

        # Verify content was added
        mock_notion_client.blocks.children.append.assert_called()

    async def test_create_research_page_no_database_id(
        self, mock_notion_client, sample_output_schema, sample_research_data
    ):
        """Test research page creation without database ID."""
        client = NotionClient("test_token")
        client.client = mock_notion_client

        with pytest.raises(NotionClientError) as exc_info:
            await client.create_research_page(
                sample_output_schema, sample_research_data
            )

        assert "No database ID provided" in str(exc_info.value)

    async def test_create_research_page_notion_api_error(
        self, sample_output_schema, sample_research_data
    ):
        """Test handling of Notion API errors."""
        from notion_client.errors import APIResponseError

        mock_client = AsyncMock()
        mock_client.pages.create.side_effect = APIResponseError(
            response=MagicMock(status=400),
            message="Bad request",
            code="validation_error",
        )

        client = NotionClient("test_token", database_id="test_db")
        client.client = mock_client

        with pytest.raises(NotionClientError) as exc_info:
            await client.create_research_page(
                sample_output_schema, sample_research_data
            )

        assert "Notion API error" in str(exc_info.value)

    async def test_update_page_properties(self, mock_notion_client):
        """Test page properties update."""
        client = NotionClient("test_token")
        client.client = mock_notion_client

        properties = {"Status": {"select": {"name": "Completed"}}}

        _ = await client.update_page_properties("test-page-123", properties)

        mock_notion_client.pages.update.assert_called_once_with(
            page_id="test-page-123", properties=properties
        )

    async def test_add_comment(self, mock_notion_client):
        """Test adding comment to page."""
        client = NotionClient("test_token")
        client.client = mock_notion_client

        comment = "This is a test comment."

        _ = await client.add_comment("test-page-123", comment)

        mock_notion_client.comments.create.assert_called_once_with(
            parent={"page_id": "test-page-123"},
            rich_text=[{"text": {"content": comment}}],
        )

    async def test_get_page_info(self, mock_notion_client):
        """Test getting page information."""
        client = NotionClient("test_token")
        client.client = mock_notion_client

        _ = await client.get_page_info("test-page-123")

        mock_notion_client.pages.retrieve.assert_called_once_with(
            page_id="test-page-123"
        )

    async def test_async_context_manager(self):
        """Test async context manager functionality."""
        async with NotionClient("test_token") as client:
            assert client.session is not None

        # Session should be closed after exiting context


class TestFormatResearchDataForNotion:
    """Test format_research_data_for_notion utility function."""

    @pytest.fixture
    def search_results(self):
        """Sample search results."""
        return [
            SearchResult(
                title="AI Research Paper",
                url="https://arxiv.org/paper1",
                snippet="Research on artificial intelligence",
                source_type=SourceType.RESEARCH_PAPERS,
                credibility_score=0.95,
                relevance_score=0.90,
                domain="arxiv.org",
                publication_date=datetime(2024, 1, 1),
                content_length=1000,
                extracted_entities=["AI", "machine learning"],
                sentiment_score=0.1,
            ),
            SearchResult(
                title="Tech News Article",
                url="https://techcrunch.com/ai-news",
                snippet="Latest AI developments",
                source_type=SourceType.NEWS,
                credibility_score=0.80,
                relevance_score=0.85,
                domain="techcrunch.com",
                publication_date=datetime(2024, 1, 2),
                content_length=800,
                extracted_entities=["OpenAI", "GPT"],
                sentiment_score=0.2,
            ),
        ]

    @pytest.fixture
    def analysis_insights(self):
        """Sample analysis insights."""
        return [
            AnalysisInsight(
                title="Key Innovation",
                content="Significant breakthrough in AI research",
                confidence_score=0.9,
                supporting_sources=["https://arxiv.org/paper1"],
                category="innovation",
                impact_level="high",
                key_entities=["AI", "breakthrough"],
            ),
            AnalysisInsight(
                title="Market Trend",
                content="Growing adoption of AI technologies",
                confidence_score=0.8,
                supporting_sources=["https://techcrunch.com/ai-news"],
                category="market",
                impact_level="medium",
                key_entities=["AI", "adoption"],
            ),
        ]

    def test_format_research_data_complete(self, search_results, analysis_insights):
        """Test formatting complete research data."""
        metadata = {
            "topic": {
                "name": "AI Research",
                "description": "Research on AI developments",
                "keywords": ["AI", "machine learning"],
                "focus_areas": ["innovations", "trends"],
            },
            "execution_id": "test-123",
            "summary": "This research explores AI developments",
            "key_points": ["Point 1", "Point 2"],
        }

        formatted_data = format_research_data_for_notion(
            search_results, analysis_insights, metadata
        )

        assert "topic" in formatted_data
        assert formatted_data["topic"]["name"] == "AI Research"

        assert "summary" in formatted_data
        assert (
            formatted_data["summary"]["text"]
            == "This research explores AI developments"
        )
        assert len(formatted_data["summary"]["key_points"]) == 2

        assert "findings" in formatted_data
        assert len(formatted_data["findings"]) == 2

        assert "sources" in formatted_data
        assert len(formatted_data["sources"]) == 2
        assert formatted_data["sources"][0]["title"] == "AI Research Paper"
        assert formatted_data["sources"][0]["credibility"] == 0.95

        assert "analysis" in formatted_data
        assert "innovation" in formatted_data["analysis"]
        assert "market" in formatted_data["analysis"]

        assert "insights" in formatted_data
        assert len(formatted_data["insights"]) == 2

        assert "metadata" in formatted_data
        assert formatted_data["metadata"]["execution_id"] == "test-123"

    def test_format_research_data_minimal(self):
        """Test formatting with minimal data."""
        formatted_data = format_research_data_for_notion([], [], {})

        assert "topic" in formatted_data
        assert "summary" in formatted_data
        assert "findings" in formatted_data
        assert "sources" in formatted_data
        assert "analysis" in formatted_data
        assert "insights" in formatted_data
        assert "metadata" in formatted_data

        # Should have default values
        assert len(formatted_data["findings"]) == 0
        assert len(formatted_data["sources"]) == 0
        assert len(formatted_data["insights"]) == 0


class TestErrorHandling:
    """Test error handling scenarios."""

    async def test_unsupported_section_type(
        self, mock_notion_client, sample_research_data
    ):
        """Test handling of unsupported section types."""
        client = NotionClient("test_token")
        client.client = mock_notion_client

        # Create a valid section but mock the handler to simulate unsupported type
        section = PageSection(
            name="Test Section", type="text_block", content_source="content"
        )

        # Mock the section type handler to be empty (simulating unsupported type)
        with patch.object(client, "_content_handlers", {}):
            # Should handle gracefully and return error message
            blocks = await client._create_section_content(
                section, "test content", sample_research_data
            )

            assert len(blocks) > 0
            # Should contain error message about unsupported section
            content = blocks[0]["paragraph"]["rich_text"][0]["text"]["content"]
            assert "Unsupported section type" in content

    async def test_section_content_creation_error(
        self, mock_notion_client, sample_research_data
    ):
        """Test handling of errors during section content creation."""
        client = NotionClient("test_token")
        client.client = mock_notion_client

        # Mock a handler that raises an exception
        def failing_handler(*args, **kwargs):
            raise Exception("Handler error")

        client._content_handlers[SectionType.TEXT_BLOCK] = failing_handler

        section = PageSection(
            name="Test Section",
            type=SectionType.TEXT_BLOCK,
            content_source="content",
        )

        blocks = await client._create_section_content(
            section, "test content", sample_research_data
        )

        assert len(blocks) > 0
        content = blocks[0]["paragraph"]["rich_text"][0]["text"]["content"]
        assert "Error rendering section" in content

    async def test_missing_content_source(
        self, mock_notion_client, sample_output_schema
    ):
        """Test handling of missing content source in research data."""
        client = NotionClient("test_token", database_id="test_db")
        client.client = mock_notion_client

        # Research data missing required content sources
        incomplete_data = {
            "topic": {"name": "Test Topic"},
            # Missing "summary", "findings", "sources"
        }

        # Should still create page but skip missing sections
        result = await client.create_research_page(
            sample_output_schema, incomplete_data
        )

        assert result["page_id"] == "test-page-123"
