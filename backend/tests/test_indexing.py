import pytest
import os
from unittest.mock import patch, MagicMock
from app.pipelines.indexing_orchestrator import reindex_document

@pytest.mark.asyncio
async def test_reindex_document_txt():
    # Setup a dummy text file
    test_file_path = "test_doc.txt"
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write("This is a test document. It has multiple sentences. We will see how it is chunked.")
    
    try:
        # We need to mock the db connections since we don't have a real TG/Chroma setup in tests
        with patch("app.pipelines.indexing_orchestrator.collection") as mock_collection, \
             patch("app.pipelines.indexing_orchestrator.tg_conn") as mock_tg_conn:
             
            # Mock Chroma DB count
            mock_collection.count.return_value = 10
            
            result = await reindex_document(test_file_path)
            
            assert result["status"] == "success"
            assert "vector_count" in result
            assert mock_collection.add.called
            assert mock_tg_conn.upsertVertex.called
            assert mock_tg_conn.upsertEdge.called
    finally:
        if os.path.exists(test_file_path):
            os.remove(test_file_path)

@pytest.mark.asyncio
async def test_reindex_document_pdf():
    # Setup a dummy PDF file (we'll just mock the PDF parser)
    test_file_path = "test_doc.pdf"
    with open(test_file_path, "wb") as f:
        f.write(b"%PDF-1.4 mock content")
        
    try:
        with patch("app.pipelines.indexing_orchestrator.collection") as mock_collection, \
             patch("app.pipelines.indexing_orchestrator.tg_conn") as mock_tg_conn, \
             patch("app.pipelines.indexing_orchestrator.extract_text_from_pdf", return_value="Mocked PDF text.") as mock_pdf_extract:
             
            mock_collection.count.return_value = 5
            
            result = await reindex_document(test_file_path)
            
            assert result["status"] == "success"
            assert mock_pdf_extract.called
            assert mock_collection.add.called
    finally:
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
