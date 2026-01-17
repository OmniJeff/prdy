"""Tests for chat functionality with mocked API calls."""
import os
import pytest
from unittest.mock import patch, MagicMock
from services.claude_service import ClaudeService, APIError
import anthropic

# client fixture is provided by conftest.py


class TestChatWithMockedAPI:
    """Tests for chat endpoint with mocked Claude API."""

    @patch.object(ClaudeService, 'chat')
    def test_chat_returns_response(self, mock_chat, client):
        """Chat should return AI response when API succeeds."""
        mock_chat.return_value = "Hello! I'm PRDy. What product would you like to build?"

        response = client.post("/api/chat", json={"message": "Hello"})

        assert response.status_code == 200
        data = response.get_json()
        assert "response" in data
        assert data["response"] == "Hello! I'm PRDy. What product would you like to build?"
        assert data["message_count"] == 2  # user + assistant

    @patch.object(ClaudeService, 'chat')
    def test_chat_maintains_conversation(self, mock_chat, client):
        """Chat should maintain conversation history across messages."""
        mock_chat.side_effect = [
            "What problem does your product solve?",
            "That's a great problem to solve. Who are your target users?"
        ]

        # First message
        response1 = client.post("/api/chat", json={"message": "I want to build a task manager"})
        assert response1.status_code == 200
        assert response1.get_json()["message_count"] == 2

        # Second message
        response2 = client.post("/api/chat", json={"message": "It helps people stay organized"})
        assert response2.status_code == 200
        assert response2.get_json()["message_count"] == 4

    @patch.object(ClaudeService, 'chat')
    def test_chat_handles_credit_error(self, mock_chat, client):
        """Chat should return friendly error when API credits are low."""
        mock_chat.side_effect = APIError(
            "API credit balance is too low. Please add credits at "
            "console.anthropic.com to continue using PRDy."
        )

        response = client.post("/api/chat", json={"message": "Hello"})

        assert response.status_code == 503
        data = response.get_json()
        assert "error" in data
        assert "credit balance" in data["error"]

    @patch.object(ClaudeService, 'chat')
    def test_chat_handles_invalid_api_key(self, mock_chat, client):
        """Chat should return friendly error for invalid API key."""
        mock_chat.side_effect = APIError(
            "Invalid API key. Please check your ANTHROPIC_API_KEY in the .env file."
        )

        response = client.post("/api/chat", json={"message": "Hello"})

        assert response.status_code == 503
        data = response.get_json()
        assert "error" in data
        assert "Invalid API key" in data["error"]

    @patch.object(ClaudeService, 'chat')
    def test_chat_handles_rate_limit(self, mock_chat, client):
        """Chat should return friendly error for rate limiting."""
        mock_chat.side_effect = APIError(
            "Rate limit exceeded. Please wait a moment and try again."
        )

        response = client.post("/api/chat", json={"message": "Hello"})

        assert response.status_code == 503
        data = response.get_json()
        assert "error" in data
        assert "Rate limit" in data["error"]

    @patch.object(ClaudeService, 'chat')
    def test_chat_error_does_not_corrupt_history(self, mock_chat, client):
        """Failed chat should not leave corrupted message history."""
        # First successful message
        mock_chat.return_value = "Hello! What would you like to build?"
        response1 = client.post("/api/chat", json={"message": "Hi"})
        assert response1.status_code == 200
        assert response1.get_json()["message_count"] == 2

        # Second message fails
        mock_chat.side_effect = APIError("API credit balance is too low")
        response2 = client.post("/api/chat", json={"message": "A task app"})
        assert response2.status_code == 503

        # Third message should work and have correct count
        mock_chat.side_effect = None
        mock_chat.return_value = "Tell me more about your idea."
        response3 = client.post("/api/chat", json={"message": "Let me try again"})
        assert response3.status_code == 200
        # Should be 4: original 2 + this new exchange of 2
        assert response3.get_json()["message_count"] == 4


class TestGeneratePRDWithMockedAPI:
    """Tests for PRD generation with mocked Claude API."""

    @patch.object(ClaudeService, 'chat')
    @patch.object(ClaudeService, 'generate_prd')
    def test_generate_prd_success(self, mock_generate, mock_chat, client):
        """Generate PRD should return PRD content and save file."""
        # Build up conversation first
        mock_chat.return_value = "Tell me about your product."
        client.post("/api/chat", json={"message": "A task manager app"})

        # Generate PRD
        mock_generate.return_value = "# Task Manager - PRD\n\n## Summary\nA task management application."

        response = client.post("/api/generate-prd")

        assert response.status_code == 200
        data = response.get_json()
        assert "prd" in data
        assert "filename" in data
        assert "Task Manager" in data["prd"]

    @patch.object(ClaudeService, 'chat')
    @patch.object(ClaudeService, 'generate_prd')
    def test_generate_prd_handles_api_error(self, mock_generate, mock_chat, client):
        """Generate PRD should handle API errors gracefully."""
        # Build up conversation first
        mock_chat.return_value = "Tell me about your product."
        client.post("/api/chat", json={"message": "A task manager app"})

        # Generate PRD fails
        mock_generate.side_effect = APIError("API credit balance is too low")

        response = client.post("/api/generate-prd")

        assert response.status_code == 503
        data = response.get_json()
        assert "error" in data
        assert "credit balance" in data["error"]

    @patch.object(ClaudeService, 'chat')
    @patch.object(ClaudeService, 'generate_prd')
    def test_saved_file_matches_ui_response(self, mock_generate, mock_chat, client, temp_output_dir):
        """CRITICAL: Saved PRD file content must exactly match what's shown in UI."""
        # Build up conversation
        mock_chat.return_value = "Tell me about your product."
        client.post("/api/chat", json={"message": "A task manager app"})

        # Create a realistic multi-line PRD
        expected_prd = """# Task Manager - Product Requirements Document

**Generated:** 2026-01-13
**Version:** 1.0

---

## 1. Executive Summary
A comprehensive task management application designed for teams.

## 2. Problem Statement
### 2.1 Current Pain Points
- Existing tools are too complex
- Poor collaboration features
- No offline support

### 2.2 Target Users
Software development teams and project managers.

## 3. Product Vision
### 3.1 Vision Statement
Simplify team task management with intuitive design.

---

*Generated with PRDy - AI-Powered PRD Assistant*"""

        mock_generate.return_value = expected_prd

        response = client.post("/api/generate-prd")

        assert response.status_code == 200
        data = response.get_json()

        # Verify UI response contains the full PRD
        assert data["prd"] == expected_prd
        assert "filename" in data

        # Verify the saved file contains EXACTLY the same content
        saved_filepath = os.path.join(temp_output_dir, data["filename"])
        assert os.path.exists(saved_filepath), f"PRD file was not saved: {saved_filepath}"

        with open(saved_filepath, "r") as f:
            saved_content = f.read()

        assert saved_content == expected_prd, (
            f"Saved file content does not match UI response!\n"
            f"UI length: {len(expected_prd)}, File length: {len(saved_content)}\n"
            f"UI content:\n{expected_prd[:200]}...\n"
            f"File content:\n{saved_content[:200]}..."
        )


class TestSessionStorage:
    """Tests for server-side session storage (fixes cookie overflow bug)."""

    @patch.object(ClaudeService, 'chat')
    def test_large_conversation_maintained(self, mock_chat, client):
        """Large conversations should be stored server-side without cookie overflow."""
        # Simulate a long response that would overflow cookie storage
        long_response = "A" * 5000  # 5KB response, exceeds 4093 byte cookie limit
        mock_chat.return_value = long_response

        # First message with long response
        response1 = client.post("/api/chat", json={"message": "Tell me everything"})
        assert response1.status_code == 200
        assert response1.get_json()["message_count"] == 2

        # Second message should still have access to conversation
        mock_chat.return_value = "Here's more info."
        response2 = client.post("/api/chat", json={"message": "Continue"})
        assert response2.status_code == 200
        assert response2.get_json()["message_count"] == 4

    @patch.object(ClaudeService, 'chat')
    @patch.object(ClaudeService, 'generate_prd')
    def test_prd_generation_after_long_conversation(self, mock_generate, mock_chat, client):
        """PRD generation should work even after long conversations."""
        # Build up a conversation with multiple exchanges
        responses = [
            "What's your product?",
            "Who are the users?",
            "What features do you need?",
            "Any technical requirements?",
        ]
        mock_chat.side_effect = responses

        for i, msg in enumerate(["App idea", "Developers", "Auth, API", "Python"]):
            response = client.post("/api/chat", json={"message": msg})
            assert response.status_code == 200
            assert response.get_json()["message_count"] == (i + 1) * 2

        # Generate PRD should have full conversation context
        expected_prd = "# Full PRD\n\nBased on our conversation..."
        mock_generate.return_value = expected_prd

        response = client.post("/api/generate-prd")
        assert response.status_code == 200
        assert response.get_json()["prd"] == expected_prd


class TestClaudeServiceErrorHandling:
    """Unit tests for ClaudeService error handling."""

    def test_handles_credit_balance_error(self):
        """Service should convert credit balance error to friendly message."""
        service = ClaudeService.__new__(ClaudeService)

        with pytest.raises(APIError) as exc_info:
            service._handle_api_error(
                Exception("credit balance is too low to access the API")
            )

        assert "credit balance is too low" in str(exc_info.value)
        assert "console.anthropic.com" in str(exc_info.value)

    def test_handles_authentication_error(self):
        """Service should convert auth error to friendly message."""
        service = ClaudeService.__new__(ClaudeService)

        with pytest.raises(APIError) as exc_info:
            service._handle_api_error(
                Exception("invalid_api_key")
            )

        assert "Invalid API key" in str(exc_info.value)

    def test_handles_rate_limit_error(self):
        """Service should convert rate limit error to friendly message."""
        service = ClaudeService.__new__(ClaudeService)

        with pytest.raises(APIError) as exc_info:
            service._handle_api_error(
                Exception("rate_limit_exceeded")
            )

        assert "Rate limit exceeded" in str(exc_info.value)

    def test_handles_overloaded_error(self):
        """Service should convert overloaded error to friendly message."""
        service = ClaudeService.__new__(ClaudeService)

        with pytest.raises(APIError) as exc_info:
            service._handle_api_error(
                Exception("API is overloaded")
            )

        assert "overloaded" in str(exc_info.value)

    def test_handles_unknown_error(self):
        """Service should pass through unknown errors with prefix."""
        service = ClaudeService.__new__(ClaudeService)

        with pytest.raises(APIError) as exc_info:
            service._handle_api_error(
                Exception("Something unexpected happened")
            )

        assert "API error:" in str(exc_info.value)
        assert "unexpected" in str(exc_info.value)
