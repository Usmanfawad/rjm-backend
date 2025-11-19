"""Unit tests for the /status endpoint."""

import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app

client = TestClient(app)


class TestStatusEndpoint:
    """Test cases for the /status endpoint."""

    def test_status_endpoint_basic(self):
        """Test that /status endpoint returns correct structure."""
        response = client.get("/status")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "status" in data
        assert "build" in data
        assert "sha" in data
        assert "env" in data
        
        # Check status value
        assert data["status"] == "ok"

    def test_status_endpoint_with_environment_variables(self):
        """Test /status endpoint with CI-injected environment variables."""
        test_env_vars = {
            "BUILD_NUMBER": "123",
            "GIT_SHA": "abc123def456",
            "ENVIRONMENT": "production"
        }
        
        with patch.dict(os.environ, test_env_vars):
            response = client.get("/status")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "ok"
            assert data["build"] == "123"
            assert data["sha"] == "abc123def456"
            assert data["env"] == "production"

    def test_status_endpoint_with_github_sha(self):
        """Test /status endpoint with GITHUB_SHA environment variable."""
        test_env_vars = {
            "BUILD_NUMBER": "456",
            "GITHUB_SHA": "github123sha456",
            "ENV": "staging"
        }
        
        with patch.dict(os.environ, test_env_vars):
            response = client.get("/status")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "ok"
            assert data["build"] == "456"
            assert data["sha"] == "github123sha456"
            assert data["env"] == "staging"

    def test_status_endpoint_local_development(self):
        """Test /status endpoint in local development (no CI env vars)."""
        # Clear relevant environment variables
        env_vars_to_clear = ["BUILD_NUMBER", "GIT_SHA", "GITHUB_SHA", "ENVIRONMENT", "ENV"]
        
        with patch.dict(os.environ, {}, clear=True):
            # Set only non-relevant env vars to avoid issues
            for var in env_vars_to_clear:
                if var in os.environ:
                    del os.environ[var]
            
            response = client.get("/status")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "ok"
            assert data["build"] == "local-dev"
            assert data["env"] == "development"
            # SHA should be either a git hash or "local-dev"
            assert data["sha"] in ["local-dev"] or len(data["sha"]) >= 8

    def test_status_endpoint_priority_order(self):
        """Test that GIT_SHA takes priority over GITHUB_SHA."""
        test_env_vars = {
            "BUILD_NUMBER": "789",
            "GIT_SHA": "priority_sha",
            "GITHUB_SHA": "fallback_sha",
            "ENVIRONMENT": "test"
        }
        
        with patch.dict(os.environ, test_env_vars):
            response = client.get("/status")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "ok"
            assert data["build"] == "789"
            assert data["sha"] == "priority_sha"  # GIT_SHA should take priority
            assert data["env"] == "test"

    def test_status_endpoint_env_priority_order(self):
        """Test that ENVIRONMENT takes priority over ENV."""
        test_env_vars = {
            "BUILD_NUMBER": "999",
            "GIT_SHA": "test_sha",
            "ENVIRONMENT": "priority_env",
            "ENV": "fallback_env"
        }
        
        with patch.dict(os.environ, test_env_vars):
            response = client.get("/status")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "ok"
            assert data["build"] == "999"
            assert data["sha"] == "test_sha"
            assert data["env"] == "priority_env"  # ENVIRONMENT should take priority
