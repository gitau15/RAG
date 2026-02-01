import os
import tempfile
from typing import List, Dict, Any
from pathlib import Path
import logging
from unstructured.partition.auto import partition
from unstructured.chunking.title import chunk_by_title
from pypdf import PdfReader
import uuid

logger = logging.getLogger(__name__)

class DocumentParser:
    """Document parser using PyPDF and Unstructured.io"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize document parser
        
        Args:
            chunk_size: Maximum size of text chunks
            chunk_overlap: Overlap between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def parse_pdf_with_pypdf(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Parse PDF using PyPDF library
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            List of document chunks with metadata
        """
        try:
            reader = PdfReader(file_path)
            chunks = []
            
            for page_num, page in enumerate(reader.pages):
                text = page.extract_text()
                if text.strip():
                    # Split text into chunks
                    page_chunks = self._split_text_into_chunks(
                        text, 
                        f"page_{page_num}",
                        file_path
                    )
                    chunks.extend(page_chunks)
            
            logger.info(f"Parsed PDF with {len(chunks)} chunks using PyPDF")
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to parse PDF with PyPDF: {str(e)}")
            raise
    
    def parse_pdf_with_unstructured(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Parse PDF using Unstructured.io library
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            List of document chunks with metadata
        """
        try:
            # Use Unstructured to parse the document
            elements = partition(filename=file_path)
            
            # Chunk by title/structure
            chunks = chunk_by_title(
                elements, 
                max_characters=self.chunk_size,
                overlap=self.chunk_overlap
            )
            
            # Convert to our format
            parsed_chunks = []
            for i, chunk in enumerate(chunks):
                parsed_chunks.append({
                    "id": str(uuid.uuid4()),
                    "content": str(chunk),
                    "metadata": {
                        "chunk_index": i,
                        "source_file": os.path.basename(file_path),
                        "file_path": file_path,
                        "parser": "unstructured"
                    }
                })
            
            logger.info(f"Parsed PDF with {len(parsed_chunks)} chunks using Unstructured")
            return parsed_chunks
            
        except Exception as e:
            logger.error(f"Failed to parse PDF with Unstructured: {str(e)}")
            raise
    
    def parse_document(self, file_path: str, method: str = "auto") -> List[Dict[str, Any]]:
        """
        Parse document using specified method or auto-detect
        
        Args:
            file_path: Path to document file
            method: Parsing method ('pypdf', 'unstructured', 'auto')
            
        Returns:
            List of document chunks with metadata
        """
        file_extension = Path(file_path).suffix.lower()
        
        # Auto-select method based on file type and quality requirements
        if method == "auto":
            if file_extension == ".pdf":
                # Try Unstructured first for better quality, fallback to PyPDF
                try:
                    return self.parse_pdf_with_unstructured(file_path)
                except Exception as e:
                    logger.warning(f"Unstructured parsing failed, falling back to PyPDF: {str(e)}")
                    return self.parse_pdf_with_pypdf(file_path)
            else:
                # For other formats, use Unstructured
                return self.parse_with_unstructured(file_path)
        elif method == "pypdf":
            return self.parse_pdf_with_pypdf(file_path)
        elif method == "unstructured":
            return self.parse_pdf_with_unstructured(file_path)
        else:
            raise ValueError(f"Unknown parsing method: {method}")
    
    def parse_with_unstructured(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Parse any supported document type using Unstructured.io
        
        Args:
            file_path: Path to document file
            
        Returns:
            List of document chunks with metadata
        """
        try:
            elements = partition(filename=file_path)
            chunks = chunk_by_title(
                elements,
                max_characters=self.chunk_size,
                overlap=self.chunk_overlap
            )
            
            parsed_chunks = []
            for i, chunk in enumerate(chunks):
                parsed_chunks.append({
                    "id": str(uuid.uuid4()),
                    "content": str(chunk),
                    "metadata": {
                        "chunk_index": i,
                        "source_file": os.path.basename(file_path),
                        "file_path": file_path,
                        "file_extension": Path(file_path).suffix,
                        "parser": "unstructured"
                    }
                })
            
            logger.info(f"Parsed document with {len(parsed_chunks)} chunks using Unstructured")
            return parsed_chunks
            
        except Exception as e:
            logger.error(f"Failed to parse document with Unstructured: {str(e)}")
            raise
    
    def _split_text_into_chunks(self, text: str, chunk_prefix: str, file_path: str) -> List[Dict[str, Any]]:
        """
        Split text into overlapping chunks
        
        Args:
            text: Text to split
            chunk_prefix: Prefix for chunk IDs
            file_path: Source file path
            
        Returns:
            List of text chunks with metadata
        """
        chunks = []
        words = text.split()
        
        # Calculate chunk parameters
        avg_word_length = sum(len(word) for word in words) / len(words) if words else 1
        words_per_chunk = int(self.chunk_size / avg_word_length)
        words_overlap = int(self.chunk_overlap / avg_word_length)
        
        start_idx = 0
        chunk_index = 0
        
        while start_idx < len(words):
            end_idx = min(start_idx + words_per_chunk, len(words))
            chunk_text = " ".join(words[start_idx:end_idx])
            
            if chunk_text.strip():
                chunks.append({
                    "id": f"{chunk_prefix}_{chunk_index}",
                    "content": chunk_text,
                    "metadata": {
                        "chunk_index": chunk_index,
                        "source_file": os.path.basename(file_path),
                        "file_path": file_path,
                        "parser": "pypdf"
                    }
                })
                chunk_index += 1
            
            # Move start index with overlap
            start_idx = end_idx - words_overlap
            if start_idx >= end_idx:  # Prevent infinite loop
                start_idx = end_idx
        
        return chunks
    
    def get_document_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extract metadata from document
        
        Args:
            file_path: Path to document file
            
        Returns:
            Dictionary with document metadata
        """
        try:
            metadata = {
                "filename": os.path.basename(file_path),
                "file_size": os.path.getsize(file_path),
                "file_extension": Path(file_path).suffix,
                "mime_type": self._get_mime_type(file_path)
            }
            
            # Extract PDF-specific metadata
            if Path(file_path).suffix.lower() == ".pdf":
                try:
                    reader = PdfReader(file_path)
                    pdf_info = reader.metadata
                    if pdf_info:
                        metadata.update({
                            "title": getattr(pdf_info, 'title', None),
                            "author": getattr(pdf_info, 'author', None),
                            "subject": getattr(pdf_info, 'subject', None),
                            "creator": getattr(pdf_info, 'creator', None),
                            "producer": getattr(pdf_info, 'producer', None),
                            "page_count": len(reader.pages)
                        })
                except Exception as e:
                    logger.warning(f"Could not extract PDF metadata: {str(e)}")
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to extract document metadata: {str(e)}")
            return {"error": str(e)}
    
    def _get_mime_type(self, file_path: str) -> str:
        """Get MIME type based on file extension"""
        extension_map = {
            '.pdf': 'application/pdf',
            '.txt': 'text/plain',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        }
        return extension_map.get(Path(file_path).suffix.lower(), 'application/octet-stream')