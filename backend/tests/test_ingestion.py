import pytest
import os
os.environ["GEMINI_API_KEY"] = "dummy-test-key"
from httpx import AsyncClient, ASGITransport
from main import app
from unittest.mock import patch, mock_open

@pytest.fixture(autouse=True)
def setup_upload_dir():
    # Ensure test upload dir exists or mock it
    os.environ["TESTING"] = "true"
    os.makedirs("backend/data/raw_uploads", exist_ok=True)
    yield
    # We could clean up test files here if necessary

@pytest.mark.asyncio
async def test_upload_valid_text_file():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        file_content = b"This is a test corpus."
        files = {"file": ("test.txt", file_content, "text/plain")}
        
        with patch("app.api.ingestion.open", mock_open()) as mocked_file:
            response = await ac.post("/api/ingestion/upload", files=files)
            
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "filename" in data["data"]
        assert data["data"]["filename"] == "test.txt"
        mocked_file.assert_called_once()

@pytest.mark.asyncio
async def test_upload_invalid_file_type():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        file_content = b"echo 'bad script'"
        files = {"file": ("test.sh", file_content, "application/x-sh")}
        
        response = await ac.post("/api/ingestion/upload", files=files)
            
        assert response.status_code == 400
        data = response.json()
        assert data["status"] == "error"
        assert "Invalid file type" in data["error"]["message"]

@pytest.mark.asyncio
async def test_upload_file_too_large():
    # Create a 51MB file payload in memory
    # To avoid memory issues in test, we just mock the size or send a large payload
    # Let's mock a file with large size via content-length or just use max size validation
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 51 MB dummy
        file_content = b"0" * (51 * 1024 * 1024)
        files = {"file": ("large.txt", file_content, "text/plain")}
        
        response = await ac.post("/api/ingestion/upload", files=files)
            
        assert response.status_code == 413
        data = response.json()
        assert data["status"] == "error"
        assert "File too large" in data["error"]["message"]
