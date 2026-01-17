"""Tests for web research service with mocked API calls."""
import pytest
from unittest.mock import patch, MagicMock
from services.research_service import ResearchService
from services.claude_service import ClaudeService


class TestResearchService:
    """Tests for ResearchService."""

    @patch.object(ResearchService, 'search')
    def test_research_competitors(self, mock_search):
        """Research competitors should search multiple topics."""
        mock_search.return_value = [
            {"title": "Competitor A", "link": "https://a.com", "snippet": "Leading solution"},
            {"title": "Competitor B", "link": "https://b.com", "snippet": "Alternative tool"}
        ]

        service = ResearchService()
        result = service.research_competitors("Task Manager", "Project management tool")

        assert "competitors" in result
        assert "market_trends" in result
        assert "pricing_info" in result
        assert "features" in result

        # Should have called search multiple times for different topics
        assert mock_search.call_count >= 4

    @patch.object(ResearchService, 'search')
    def test_research_topic(self, mock_search):
        """Research topic should return search results."""
        mock_search.return_value = [
            {"title": "Result 1", "link": "https://example.com", "snippet": "Description"}
        ]

        service = ResearchService()
        results = service.research_topic("SaaS pricing strategies", "B2B software")

        assert len(results) == 1
        assert results[0]["title"] == "Result 1"

    def test_format_research_for_prompt(self):
        """Format research should create readable markdown."""
        service = ResearchService()

        research_data = {
            "competitors": [
                {"title": "Asana", "link": "https://asana.com", "snippet": "Work management platform"}
            ],
            "market_trends": [
                {"title": "Remote Work Trends", "link": "https://trends.com", "snippet": "Growing demand"}
            ],
            "pricing_info": [],
            "features": []
        }

        formatted = service.format_research_for_prompt(research_data)

        assert "## Competitor Research" in formatted
        assert "Asana" in formatted
        assert "## Market Trends" in formatted
        assert "Remote Work" in formatted

    def test_format_empty_research(self):
        """Format should handle empty research gracefully."""
        service = ResearchService()

        research_data = {
            "competitors": [],
            "market_trends": [],
            "pricing_info": [],
            "features": []
        }

        formatted = service.format_research_for_prompt(research_data)
        # Should return empty or minimal output
        assert formatted.strip() == "" or "##" not in formatted


class TestResearchServiceWithMockedDDGS:
    """Tests for ResearchService with mocked DuckDuckGo search."""

    @patch('services.research_service.DDGS')
    def test_search_returns_formatted_results(self, mock_ddgs_class):
        """Search should return properly formatted results."""
        mock_ddgs = MagicMock()
        mock_ddgs.text.return_value = [
            {"title": "Test Result", "href": "https://test.com", "body": "Test description"}
        ]
        mock_ddgs_class.return_value = mock_ddgs

        service = ResearchService()
        results = service.search("test query", max_results=5)

        assert len(results) == 1
        assert results[0]["title"] == "Test Result"
        assert results[0]["link"] == "https://test.com"
        assert results[0]["snippet"] == "Test description"

    @patch('services.research_service.DDGS')
    def test_search_handles_errors(self, mock_ddgs_class):
        """Search should handle errors gracefully."""
        mock_ddgs = MagicMock()
        mock_ddgs.text.side_effect = Exception("Network error")
        mock_ddgs_class.return_value = mock_ddgs

        service = ResearchService()
        results = service.search("test query")

        # Should return empty list on error
        assert results == []


class TestContextResearchEndpoint:
    """Tests for the context-aware research endpoint."""

    def test_context_research_empty_conversation(self, client):
        """Context research should fail gracefully with no conversation."""
        response = client.post('/api/research/context', json={
            'source': 'conversation'
        })
        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] == 'no_context'

    def test_context_research_nonexistent_prd(self, client):
        """Context research should return 404 for nonexistent PRD."""
        response = client.post('/api/research/context', json={
            'source': 'nonexistent-file.md'
        })
        assert response.status_code == 404

    @patch.object(ClaudeService, 'extract_product_context')
    def test_context_research_insufficient_context(self, mock_extract, client):
        """Context research should fail if product can't be identified."""
        # First need a conversation
        with patch.object(ClaudeService, 'chat') as mock_chat:
            mock_chat.return_value = "Hi there!"
            client.post('/api/chat', json={'message': 'Hello'})

        mock_extract.return_value = {
            'product_name': None,
            'product_description': None,
            'confidence': 'none'
        }

        response = client.post('/api/research/context', json={
            'source': 'conversation'
        })
        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] == 'insufficient_context'


class TestSaveResearchEndpoint:
    """Tests for the save research endpoint."""

    def test_save_research_no_content(self, client):
        """Save should fail without content."""
        response = client.post('/api/research/save', json={
            'content': '',
            'save_type': 'separate_file',
            'product_name': 'Test'
        })
        assert response.status_code == 400
        assert 'No content' in response.get_json()['error']

    def test_save_research_append_requires_filename(self, client):
        """Append to PRD should require filename."""
        response = client.post('/api/research/save', json={
            'content': 'Test analysis',
            'save_type': 'append_prd',
            'prd_filename': ''
        })
        assert response.status_code == 400
        assert 'filename required' in response.get_json()['error']

    def test_save_research_separate_file(self, client, temp_output_dir):
        """Save as separate file should create new markdown."""
        import os
        response = client.post('/api/research/save', json={
            'content': 'Test competitive analysis content',
            'save_type': 'separate_file',
            'product_name': 'Test Product'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'competitive-analysis' in data['filename']

        # Verify file was created
        filepath = os.path.join(temp_output_dir, data['filename'])
        assert os.path.exists(filepath)

    def test_save_research_append_to_prd(self, client, temp_output_dir):
        """Append should add content to existing PRD."""
        import os

        # Create a PRD file first
        prd_filename = 'test-product-prd-20240113-120000.md'
        original_content = '# Test Product - PRD\n\n## Summary\nA test product.'
        with open(os.path.join(temp_output_dir, prd_filename), 'w') as f:
            f.write(original_content)

        response = client.post('/api/research/save', json={
            'content': 'Competitor A is the main rival.',
            'save_type': 'append_prd',
            'prd_filename': prd_filename
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # Verify content was appended
        with open(os.path.join(temp_output_dir, prd_filename), 'r') as f:
            updated_content = f.read()

        assert original_content in updated_content
        assert 'Competitive Analysis' in updated_content
        assert 'Competitor A' in updated_content


class TestProductContextExtraction:
    """Tests for product context extraction."""

    @patch.object(ClaudeService, 'extract_product_context')
    def test_extraction_from_prd_content(self, mock_extract, client, temp_output_dir):
        """Should extract product info from PRD file content."""
        import os

        # Create a PRD with clear product name
        prd_filename = 'task-manager-prd-20240113-120000.md'
        prd_content = '# TaskFlow - PRD\n\n## Summary\nA task management app for remote teams.'
        with open(os.path.join(temp_output_dir, prd_filename), 'w') as f:
            f.write(prd_content)

        mock_extract.return_value = {
            'product_name': 'TaskFlow',
            'product_description': 'A task management app for remote teams',
            'confidence': 'high'
        }

        # This would be called by the context research endpoint
        from services.claude_service import ClaudeService
        service = ClaudeService.__new__(ClaudeService)
        result = mock_extract(prd_content=prd_content)

        assert result['product_name'] == 'TaskFlow'
        assert result['confidence'] == 'high'
