import re
import uuid
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@dataclass
class LegalCitation:
    """Represents a legal document citation"""
    citation_id: str
    source_document: str
    source_file: str
    page_number: Optional[int]
    section: Optional[str]
    paragraph: Optional[str]
    chunk_id: str
    content_snippet: str
    relevance_score: float
    timestamp: datetime

@dataclass
class CitationContext:
    """Context for citation tracking"""
    query: str
    mode: str
    collection_name: str
    tenant_id: Optional[str]
    retrieved_documents: List[Dict[str, Any]]

class CitationEngine:
    """Legal document citation tracking engine"""
    
    def __init__(self):
        self.citations = {}  # Store citations by session/query
        self.citation_patterns = {
            'case_law': r'\b(v\.|vs\.|versus|In\s+re|Ex\s+parte|In\s+the\s+Matter\s+of)\b',
            'statute': r'\b(\d+\s+U\.S\.C\.|\d+\s+Stat\.|\d+\s+U\.S\.)\b',
            'regulation': r'\b(\d+\s+CFR\s+§|Title\s+\d+\s+of\s+the\s+Code\s+of\s+Federal\s+Regulations)\b',
            'court': r'\b(Supreme\s+Court|Court\s+of\s+Appeals|District\s+Court|Circuit\s+Court)\b'
        }
    
    def generate_citations(self, context: CitationContext) -> List[LegalCitation]:
        """
        Generate citations from retrieved documents
        
        Args:
            context: Citation context with query and retrieved documents
            
        Returns:
            List of legal citations
        """
        citations = []
        
        for i, doc in enumerate(context.retrieved_documents):
            try:
                citation = self._create_citation_from_document(doc, context, i)
                if citation:
                    citations.append(citation)
            except Exception as e:
                logger.error(f"Error creating citation for document {i}: {str(e)}")
                continue
        
        # Store citations for this context
        context_id = f"{context.tenant_id or 'default'}_{hash(context.query)}_{int(datetime.now().timestamp())}"
        self.citations[context_id] = citations
        
        logger.info(f"Generated {len(citations)} citations for query: {context.query[:50]}...")
        return citations
    
    def _create_citation_from_document(self, doc: Dict[str, Any], context: CitationContext, index: int) -> Optional[LegalCitation]:
        """Create a citation from a document"""
        try:
            metadata = doc.get('metadata', {})
            content = doc.get('content', '')
            
            # Extract legal identifiers
            page_number = self._extract_page_number(content, metadata)
            section = self._extract_section(content, metadata)
            paragraph = self._extract_paragraph(content, metadata)
            
            # Create content snippet
            snippet = self._create_content_snippet(content)
            
            # Calculate relevance score
            relevance_score = self._calculate_relevance_score(doc, context.query)
            
            return LegalCitation(
                citation_id=f"cit_{uuid.uuid4().hex[:8]}",
                source_document=metadata.get('source_file', 'Unknown'),
                source_file=metadata.get('file_path', ''),
                page_number=page_number,
                section=section,
                paragraph=paragraph,
                chunk_id=doc.get('id', ''),
                content_snippet=snippet,
                relevance_score=relevance_score,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error creating citation: {str(e)}")
            return None
    
    def _extract_page_number(self, content: str, metadata: Dict[str, Any]) -> Optional[int]:
        """Extract page number from document"""
        # Try metadata first
        if 'page_number' in metadata:
            try:
                return int(metadata['page_number'])
            except (ValueError, TypeError):
                pass
        
        # Try content patterns
        page_patterns = [
            r'Page\s+(\d+)',
            r'PAGE\s+(\d+)',
            r'(\d+)\s*of\s*\d+',
            r'^\s*(\d+)\s*$'  # Page number at start of line
        ]
        
        for pattern in page_patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
            if match:
                try:
                    return int(match.group(1))
                except (ValueError, IndexError):
                    continue
        
        return metadata.get('chunk_index')  # Fallback to chunk index
    
    def _extract_section(self, content: str, metadata: Dict[str, Any]) -> Optional[str]:
        """Extract section identifier"""
        # Try metadata
        if 'section' in metadata:
            return str(metadata['section'])
        
        # Try common section patterns
        section_patterns = [
            r'Section\s+([A-Z0-9.-]+)',
            r'§\s*([A-Z0-9.-]+)',
            r'Art\.\s*([A-Z0-9.-]+)',  # Article
            r'Rule\s+([A-Z0-9.-]+)'
        ]
        
        for pattern in section_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_paragraph(self, content: str, metadata: Dict[str, Any]) -> Optional[str]:
        """Extract paragraph identifier"""
        # Try metadata
        if 'paragraph' in metadata:
            return str(metadata['paragraph'])
        
        # Look for paragraph markers
        para_patterns = [
            r'¶\s*([A-Z0-9.-]+)',
            r'Paragraph\s+([A-Z0-9.-]+)',
            r'\(\s*([a-z])\s*\)',  # (a), (b), etc.
        ]
        
        for pattern in para_patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1)
        
        return None
    
    def _create_content_snippet(self, content: str, max_length: int = 200) -> str:
        """Create a meaningful content snippet"""
        if len(content) <= max_length:
            return content.strip()
        
        # Try to find a sentence boundary
        sentence_end = content.rfind('.', 0, max_length)
        if sentence_end > max_length * 0.7:  # Good sentence boundary found
            return content[:sentence_end + 1].strip()
        else:
            # Truncate at word boundary
            word_end = content.rfind(' ', 0, max_length)
            if word_end > 0:
                return content[:word_end].strip() + "..."
            else:
                return content[:max_length].strip() + "..."
    
    def _calculate_relevance_score(self, doc: Dict[str, Any], query: str) -> float:
        """Calculate relevance score based on document metadata and content"""
        score = 0.0
        content = doc.get('content', '').lower()
        query_lower = query.lower()
        
        # Content similarity (basic keyword matching)
        query_words = query_lower.split()
        content_words = content.split()
        
        if content_words:
            matched_words = sum(1 for word in query_words if word in content_words)
            keyword_score = matched_words / len(query_words)
            score += keyword_score * 0.5  # Weight keyword matching
        
        # Metadata factors
        metadata = doc.get('metadata', {})
        if metadata.get('mode') == 'judicial':
            score += 0.2  # Boost for judicial documents
        if metadata.get('parser_used') == 'unstructured':
            score += 0.1  # Slight boost for higher quality parsing
        
        # Distance score (lower distance = higher relevance)
        distance = doc.get('distance')
        if distance is not None:
            # Convert distance to relevance (0-1 scale)
            distance_score = max(0, 1 - float(distance))
            score += distance_score * 0.2
        
        return min(1.0, max(0.0, score))  # Normalize to 0-1 range
    
    def format_citations_for_response(self, citations: List[LegalCitation]) -> List[Dict[str, Any]]:
        """
        Format citations for API response
        
        Args:
            citations: List of legal citations
            
        Returns:
            Formatted citation data for response
        """
        formatted_citations = []
        
        for citation in citations:
            formatted_citation = {
                "id": citation.citation_id,
                "source": {
                    "document": citation.source_document,
                    "file": citation.source_file
                },
                "location": {
                    "page": citation.page_number,
                    "section": citation.section,
                    "paragraph": citation.paragraph
                },
                "content": citation.content_snippet,
                "chunk_id": citation.chunk_id,
                "relevance_score": round(citation.relevance_score, 3),
                "timestamp": citation.timestamp.isoformat()
            }
            formatted_citations.append(formatted_citation)
        
        return formatted_citations
    
    def validate_citation_chain(self, citations: List[LegalCitation]) -> Dict[str, Any]:
        """
        Validate and analyze the citation chain for completeness and quality
        
        Args:
            citations: List of citations to validate
            
        Returns:
            Validation results and chain analysis
        """
        if not citations:
            return {"valid": False, "issues": ["No citations found"]}
        
        issues = []
        stats = {
            "total_citations": len(citations),
            "unique_sources": len(set(c.source_document for c in citations)),
            "avg_relevance": sum(c.relevance_score for c in citations) / len(citations),
            "citations_with_page": sum(1 for c in citations if c.page_number is not None),
            "citations_with_section": sum(1 for c in citations if c.section is not None)
        }
        
        # Check for completeness
        if stats["citations_with_page"] < len(citations) * 0.5:
            issues.append("Many citations lack page numbers")
        
        if stats["citations_with_section"] < len(citations) * 0.3:
            issues.append("Many citations lack section identifiers")
        
        # Check relevance distribution
        low_relevance_citations = [c for c in citations if c.relevance_score < 0.3]
        if len(low_relevance_citations) > len(citations) * 0.3:
            issues.append("High percentage of low-relevance citations")
        
        # Check for duplicate sources
        source_counts = {}
        for citation in citations:
            source = citation.source_document
            source_counts[source] = source_counts.get(source, 0) + 1
        
        duplicate_sources = [source for source, count in source_counts.items() if count > 3]
        if duplicate_sources:
            issues.append(f"Over-reliance on sources: {', '.join(duplicate_sources[:3])}")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "statistics": stats,
            "quality_score": self._calculate_chain_quality_score(stats, issues)
        }
    
    def _calculate_chain_quality_score(self, stats: Dict[str, Any], issues: List[str]) -> float:
        """Calculate overall quality score for citation chain"""
        score = 1.0
        
        # Penalty for issues
        score -= len(issues) * 0.1
        
        # Bonus for completeness
        completeness_bonus = (stats["citations_with_page"] + stats["citations_with_section"]) / (stats["total_citations"] * 2)
        score += completeness_bonus * 0.2
        
        # Bonus for relevance
        score += stats["avg_relevance"] * 0.3
        
        return max(0.0, min(1.0, score))
    
    def get_citation_history(self, context_id: str) -> List[LegalCitation]:
        """Get citation history for a specific context"""
        return self.citations.get(context_id, [])

# Global instance
citation_engine = CitationEngine()