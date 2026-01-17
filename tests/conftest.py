"""Shared test fixtures."""
import os
import tempfile
import pytest


@pytest.fixture
def temp_output_dir(monkeypatch):
    """Create a temporary output directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Patch the OUTPUT_DIR in config before importing app
        import config
        monkeypatch.setattr(config, "OUTPUT_DIR", tmpdir)
        yield tmpdir


@pytest.fixture
def client(temp_output_dir):
    """Create a test client with isolated output directory."""
    # Import app after patching config
    from app import app, prd_service

    # Update the prd_service's output_dir to use temp directory
    prd_service.output_dir = temp_output_dir

    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key"
    with app.test_client() as test_client:
        yield test_client
