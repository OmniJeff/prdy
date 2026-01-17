"""Tests for PRDy application routes and functionality."""
import pytest

# client fixture is provided by conftest.py


class TestIndexRoute:
    """Tests for the main index route - verifies the blank page bug is fixed."""

    def test_index_returns_200(self, client):
        """Index route should return 200 status code."""
        response = client.get("/")
        assert response.status_code == 200

    def test_index_returns_html(self, client):
        """Index route should return HTML content."""
        response = client.get("/")
        assert response.content_type.startswith("text/html")

    def test_index_contains_prdy_title(self, client):
        """Index page should contain the PRDy title."""
        response = client.get("/")
        assert b"PRDy" in response.data

    def test_index_contains_chat_container(self, client):
        """Index page should contain the chat container element."""
        response = client.get("/")
        assert b"chat-container" in response.data

    def test_index_contains_required_elements(self, client):
        """Index page should contain all required UI elements."""
        response = client.get("/")
        html = response.data.decode("utf-8")

        # Check for essential elements
        assert "chat-messages" in html
        assert "message-input" in html
        assert "send-btn" in html
        assert "generate-btn" in html

    def test_index_not_empty(self, client):
        """Index route should not return empty content (blank page bug)."""
        response = client.get("/")
        assert len(response.data) > 100  # Should have substantial content


class TestStaticFiles:
    """Tests for static file serving."""

    def test_css_file_served(self, client):
        """CSS file should be accessible."""
        response = client.get("/static/css/style.css")
        assert response.status_code == 200
        assert "text/css" in response.content_type

    def test_js_file_served(self, client):
        """JavaScript file should be accessible."""
        response = client.get("/static/js/chat.js")
        assert response.status_code == 200
        assert "javascript" in response.content_type

    def test_css_contains_styles(self, client):
        """CSS file should contain actual style definitions."""
        response = client.get("/static/css/style.css")
        css_content = response.data.decode("utf-8")
        assert "background" in css_content
        assert "color" in css_content

    def test_js_contains_code(self, client):
        """JavaScript file should contain actual code."""
        response = client.get("/static/js/chat.js")
        js_content = response.data.decode("utf-8")
        assert "addEventListener" in js_content
        assert "fetch" in js_content


class TestAPIRoutes:
    """Tests for API endpoints."""

    def test_chat_requires_message(self, client):
        """Chat endpoint should require a message."""
        response = client.post("/api/chat", json={})
        assert response.status_code == 400

    def test_chat_rejects_empty_message(self, client):
        """Chat endpoint should reject empty messages."""
        response = client.post("/api/chat", json={"message": ""})
        assert response.status_code == 400

    def test_generate_prd_requires_conversation(self, client):
        """Generate PRD should require prior conversation."""
        response = client.post("/api/generate-prd", json={})
        assert response.status_code == 400

    def test_list_prds_returns_json(self, client):
        """List PRDs endpoint should return JSON."""
        response = client.get("/api/prds")
        assert response.status_code == 200
        assert response.content_type == "application/json"

    def test_clear_conversation(self, client):
        """Clear endpoint should work."""
        response = client.post("/api/clear")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    def test_get_nonexistent_prd_returns_404(self, client):
        """Getting a non-existent PRD should return 404."""
        response = client.get("/api/prds/nonexistent-file.md")
        assert response.status_code == 404

    def test_load_nonexistent_prd_returns_404(self, client):
        """Loading a non-existent PRD for iteration should return 404."""
        response = client.post("/api/load-prd/nonexistent-file.md")
        assert response.status_code == 404


class TestLoadPRD:
    """Tests for loading existing PRDs for iteration."""

    def test_load_prd_success(self, client, temp_output_dir):
        """Loading an existing PRD should initialize conversation context."""
        import os
        # Create a test PRD file
        test_content = "# Test Product - PRD\n\n## Summary\nA test product."
        test_filename = "test-product-prd-20240113-120000.md"
        with open(os.path.join(temp_output_dir, test_filename), "w") as f:
            f.write(test_content)

        response = client.post(f"/api/load-prd/{test_filename}")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["content"] == test_content
        assert data["filename"] == test_filename
        assert data["message_count"] == 2  # user message + assistant response

    def test_load_prd_enables_generate(self, client, temp_output_dir):
        """After loading a PRD, chat should work and maintain context."""
        import os
        from unittest.mock import patch
        from services.claude_service import ClaudeService

        # Create a test PRD file
        test_content = "# My App - PRD\n\n## Summary\nAn app."
        test_filename = "my-app-prd-20240113-120000.md"
        with open(os.path.join(temp_output_dir, test_filename), "w") as f:
            f.write(test_content)

        # Load the PRD
        response = client.post(f"/api/load-prd/{test_filename}")
        assert response.status_code == 200

        # Send a follow-up message
        with patch.object(ClaudeService, 'chat') as mock_chat:
            mock_chat.return_value = "I'll help you add that feature."
            response = client.post("/api/chat", json={"message": "Add a login feature"})

            assert response.status_code == 200
            data = response.get_json()
            # Should be 4: 2 from load + 2 from this exchange
            assert data["message_count"] == 4


class TestListPRDsFormat:
    """Tests for the PRD listing format."""

    def test_list_prds_includes_name_and_date(self, client, temp_output_dir):
        """List PRDs should return formatted name and date fields."""
        import os
        # Create a test PRD file
        test_filename = "task-manager-prd-20240113-120000.md"
        with open(os.path.join(temp_output_dir, test_filename), "w") as f:
            f.write("# Task Manager - PRD")

        response = client.get("/api/prds")

        assert response.status_code == 200
        data = response.get_json()
        assert len(data["prds"]) == 1

        prd = data["prds"][0]
        assert prd["filename"] == test_filename
        assert prd["name"] == "Task Manager"
        assert "date" in prd  # Should have formatted date

    def test_list_prds_sorted_by_date(self, client, temp_output_dir):
        """List PRDs should be sorted by date, newest first."""
        import os
        import time

        # Create two PRD files with different timestamps
        files = [
            "older-prd-20240101-100000.md",
            "newer-prd-20240115-100000.md"
        ]
        for filename in files:
            with open(os.path.join(temp_output_dir, filename), "w") as f:
                f.write(f"# {filename}")
            time.sleep(0.1)  # Ensure different timestamps

        response = client.get("/api/prds")
        data = response.get_json()

        # Newer file should be first (created more recently due to time.sleep)
        assert data["prds"][0]["filename"] == "newer-prd-20240115-100000.md"


class TestResearchEndpoints:
    """Tests for web research endpoints."""

    def test_research_requires_product_name(self, client):
        """Competitor research should require a product name."""
        response = client.post("/api/research", json={
            "type": "competitors",
            "product_name": ""
        })
        assert response.status_code == 400
        assert "Product name is required" in response.get_json()["error"]

    def test_custom_research_requires_query(self, client):
        """Custom research should require a query."""
        response = client.post("/api/research", json={
            "type": "custom",
            "query": ""
        })
        assert response.status_code == 400
        assert "Query is required" in response.get_json()["error"]

    def test_research_invalid_type(self, client):
        """Research should reject invalid type."""
        response = client.post("/api/research", json={
            "type": "invalid",
            "product_name": "Test Product"
        })
        assert response.status_code == 400
        assert "Invalid research type" in response.get_json()["error"]

    def test_search_requires_query(self, client):
        """Simple search endpoint should require a query."""
        response = client.post("/api/research/search", json={
            "query": ""
        })
        assert response.status_code == 400
        assert "Query is required" in response.get_json()["error"]
