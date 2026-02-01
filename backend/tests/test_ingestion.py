import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

from app.ingestion.document_parser import DocumentParser
from app.ingestion.ingestion_pipeline import IngestionPipeline

class TestDocumentParser:
    """Test document parsing functionality"""
    
    def test_split_text_into_chunks(self):
        """Test text chunking functionality"""
        parser = DocumentParser(chunk_size=100, chunk_overlap=20)
        
        # Create test text
        test_text = " ".join(["word"] * 50)  # 50 words
        chunks = parser._split_text_into_chunks(test_text, "test", "test.pdf")
        
        assert len(chunks) > 0
        assert all("content" in chunk for chunk in chunks)
        assert all("metadata" in chunk for chunk in chunks)
    
    @patch('app.ingestion.document_parser.PdfReader')
    def test_parse_pdf_with_pypdf(self, mock_pdf_reader):
        """Test PDF parsing with PyPDF"""
        # Mock PDF reader
        mock_page = Mock()
        mock_page.extract_text.return_value = "Test PDF content"
        mock_pdf_reader.return_value.pages = [mock_page]
        
        parser = DocumentParser()
        chunks = parser.parse_pdf_with_pypdf("test.pdf")
        
        assert len(chunks) > 0
        assert chunks[0]["content"] == "Test PDF content"
    
    def test_get_document_metadata(self):
        """Test document metadata extraction"""
        parser = DocumentParser()
        
        # Create temporary test file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(b"test content")
            tmp_path = tmp.name
        
        try:
            metadata = parser.get_document_metadata(tmp_path)
            assert "filename" in metadata
            assert "file_size" in metadata
            assert "file_extension" in metadata
        finally:
            os.unlink(tmp_path)

class TestIngestionPipeline:
    """Test ingestion pipeline functionality"""
    
    @pytest.fixture
    def pipeline(self):
        """Create pipeline instance with mocked dependencies"""
        with patch('app.ingestion.ingestion_pipeline.chroma_client'), \
             patch('app.ingestion.ingestion_pipeline.embedding_manager'):
            return IngestionPipeline()
    
    def test_save_temporary_file(self, pipeline):
        """Test temporary file saving"""
        test_content = b"test document content"
        filename = "test.pdf"
        
        async def run_test():
            temp_path = await pipeline._save_temporary_file(test_content, filename)
            assert os.path.exists(temp_path)
            assert Path(temp_path).name.endswith(filename)
            
            # Cleanup
            await pipeline._cleanup_temporary_file(temp_path)
            assert not os.path.exists(temp_path)
        
        import asyncio
        asyncio.run(run_test())
    
    @patch('app.ingestion.ingestion_pipeline.DocumentParser')
    def test_ensure_collection(self, mock_parser, pipeline):
        """Test collection creation/retrieval"""
        mock_parser.return_value.parse_document.return_value = [
            {"id": "chunk1", "content": "test", "metadata": {}}
        ]
        
        async def run_test():
            collection = await pipeline._ensure_collection("test_collection", "tenant1", "judicial")
            assert collection is not None
        
        import asyncio
        asyncio.run(run_test())

if __name__ == "__main__":
    pytest.main([__file__])