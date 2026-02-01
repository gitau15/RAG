import re
from typing import List, Dict, Any
from .citation_engine import LegalCitation

class LegalFormatter:
    """Formatter for legal citations in various styles"""
    
    @staticmethod
    def format_citation_apa(citation: LegalCitation) -> str:
        """Format citation in APA style"""
        parts = []
        
        # Source document (case name or statute title)
        if citation.source_document:
            parts.append(f"{citation.source_document}")
        
        # Year (if available in metadata)
        # parts.append("(2024)")  # Would come from metadata
        
        # Section/page information
        location_parts = []
        if citation.section:
            location_parts.append(f"§ {citation.section}")
        if citation.page_number:
            location_parts.append(f"p. {citation.page_number}")
        if citation.paragraph:
            location_parts.append(f"¶ {citation.paragraph}")
        
        if location_parts:
            parts.append("(" + ", ".join(location_parts) + ")")
        
        return " ".join(parts)
    
    @staticmethod
    def format_citation_bluebook(citation: LegalCitation) -> str:
        """Format citation in Bluebook style"""
        parts = []
        
        # Source document
        if citation.source_document:
            parts.append(f"{citation.source_document}")
        
        # Volume and reporter (would come from metadata)
        # parts.append("123 F.3d 456")
        
        # Page number
        if citation.page_number:
            parts.append(f"{citation.page_number}")
        
        # Section/paragraph
        if citation.section:
            parts.append(f"§ {citation.section}")
        if citation.paragraph:
            parts.append(f"¶ {citation.paragraph}")
        
        return " ".join(parts)
    
    @staticmethod
    def format_citation_oscola(citation: LegalCitation) -> str:
        """Format citation in OSCOLA style (Oxford Standard for Citation of Legal Authorities)"""
        parts = []
        
        # Source document
        if citation.source_document:
            parts.append(f"[{citation.source_document}]")
        
        # Year (if available)
        # parts.append("[2024]")
        
        # Page number
        if citation.page_number:
            parts.append(f"{citation.page_number}")
        
        # Section/paragraph
        if citation.section:
            parts.append(f"[{citation.section}]")
        if citation.paragraph:
            parts.append(f"[{citation.paragraph}]")
        
        return " ".join(parts)
    
    @staticmethod
    def format_citation_chicago(citation: LegalCitation) -> str:
        """Format citation in Chicago style"""
        parts = []
        
        # Source document
        if citation.source_document:
            parts.append(f'"{citation.source_document}"')
        
        # Additional details
        details = []
        if citation.section:
            details.append(f"§ {citation.section}")
        if citation.page_number:
            details.append(f"at {citation.page_number}")
        if citation.paragraph:
            details.append(f"¶ {citation.paragraph}")
        
        if details:
            parts.append("(" + ", ".join(details) + ")")
        
        return " ".join(parts)
    
    @staticmethod
    def format_citations_html(citations: List[LegalCitation], style: str = "apa") -> str:
        """Format citations as HTML for web display"""
        formatter_map = {
            "apa": LegalFormatter.format_citation_apa,
            "bluebook": LegalFormatter.format_citation_bluebook,
            "oscola": LegalFormatter.format_citation_oscola,
            "chicago": LegalFormatter.format_citation_chicago
        }
        
        formatter = formatter_map.get(style.lower(), LegalFormatter.format_citation_apa)
        
        html_parts = ['<div class="legal-citations">']
        html_parts.append('<h4>Legal Citations</h4>')
        html_parts.append('<ol class="citation-list">')
        
        for i, citation in enumerate(citations, 1):
            formatted_citation = formatter(citation)
            html_parts.append(f'<li class="citation-item">')
            html_parts.append(f'  <span class="citation-number">[{i}]</span>')
            html_parts.append(f'  <span class="citation-text">{formatted_citation}</span>')
            html_parts.append(f'  <div class="citation-source">Source: {citation.source_document}</div>')
            if citation.page_number:
                html_parts.append(f'  <div class="citation-page">Page: {citation.page_number}</div>')
            html_parts.append('</li>')
        
        html_parts.append('</ol>')
        html_parts.append('</div>')
        
        return '\n'.join(html_parts)
    
    @staticmethod
    def format_citations_markdown(citations: List[LegalCitation], style: str = "apa") -> str:
        """Format citations as Markdown"""
        formatter_map = {
            "apa": LegalFormatter.format_citation_apa,
            "bluebook": LegalFormatter.format_citation_bluebook,
            "oscola": LegalFormatter.format_citation_oscola,
            "chicago": LegalFormatter.format_citation_chicago
        }
        
        formatter = formatter_map.get(style.lower(), LegalFormatter.format_citation_apa)
        
        markdown_lines = ["## Legal Citations\n"]
        
        for i, citation in enumerate(citations, 1):
            formatted_citation = formatter(citation)
            markdown_lines.append(f"{i}. {formatted_citation}")
            markdown_lines.append(f"   - Source: {citation.source_document}")
            if citation.page_number:
                markdown_lines.append(f"   - Page: {citation.page_number}")
            if citation.section:
                markdown_lines.append(f"   - Section: {citation.section}")
            markdown_lines.append("")
        
        return "\n".join(markdown_lines)
    
    @staticmethod
    def generate_citation_summary(citations: List[LegalCitation]) -> Dict[str, Any]:
        """Generate a summary of citation patterns and statistics"""
        if not citations:
            return {"summary": "No citations available"}
        
        # Group by source
        source_groups = {}
        section_stats = {}
        page_stats = {"with_page": 0, "without_page": 0}
        
        for citation in citations:
            # Source grouping
            source = citation.source_document
            if source not in source_groups:
                source_groups[source] = []
            source_groups[source].append(citation)
            
            # Section statistics
            if citation.section:
                section_stats[citation.section] = section_stats.get(citation.section, 0) + 1
            
            # Page statistics
            if citation.page_number is not None:
                page_stats["with_page"] += 1
            else:
                page_stats["without_page"] += 1
        
        # Summary statistics
        summary = {
            "total_citations": len(citations),
            "unique_sources": len(source_groups),
            "sources_breakdown": {
                source: len(citations) for source, citations in source_groups.items()
            },
            "section_distribution": dict(sorted(section_stats.items(), 
                                              key=lambda x: x[1], reverse=True)[:10]),
            "page_coverage": {
                "with_page_numbers": page_stats["with_page"],
                "without_page_numbers": page_stats["without_page"],
                "coverage_percentage": round(
                    (page_stats["with_page"] / len(citations)) * 100, 1
                ) if citations else 0
            },
            "relevance_distribution": {
                "high": len([c for c in citations if c.relevance_score >= 0.7]),
                "medium": len([c for c in citations if 0.4 <= c.relevance_score < 0.7]),
                "low": len([c for c in citations if c.relevance_score < 0.4])
            }
        }
        
        return summary

class CitationValidator:
    """Validator for legal citation quality and completeness"""
    
    @staticmethod
    def validate_citation_completeness(citation: LegalCitation) -> Dict[str, Any]:
        """Validate completeness of a single citation"""
        issues = []
        completeness_score = 1.0
        
        # Check required fields
        if not citation.source_document or citation.source_document == "Unknown":
            issues.append("Missing source document name")
            completeness_score -= 0.3
        
        # Check location information
        location_provided = any([
            citation.page_number is not None,
            citation.section is not None,
            citation.paragraph is not None
        ])
        
        if not location_provided:
            issues.append("No location information (page, section, or paragraph)")
            completeness_score -= 0.4
        elif sum([citation.page_number is not None, 
                  citation.section is not None, 
                  citation.paragraph is not None]) == 1:
            # Only one location identifier - partial penalty
            completeness_score -= 0.1
        
        # Check content snippet
        if not citation.content_snippet or len(citation.content_snippet.strip()) < 10:
            issues.append("Content snippet too short or missing")
            completeness_score -= 0.2
        
        # Check relevance score
        if citation.relevance_score < 0.3:
            issues.append("Low relevance score")
            completeness_score -= 0.1
        
        return {
            "valid": len(issues) == 0,
            "completeness_score": max(0.0, completeness_score),
            "issues": issues,
            "recommendations": CitationValidator._generate_recommendations(issues)
        }
    
    @staticmethod
    def _generate_recommendations(issues: List[str]) -> List[str]:
        """Generate recommendations based on validation issues"""
        recommendations = []
        
        if "Missing source document name" in issues:
            recommendations.append("Ensure document metadata includes proper source names")
        
        if "No location information" in issues:
            recommendations.append("Add page numbers, sections, or paragraph identifiers to documents")
        
        if "Content snippet too short" in issues:
            recommendations.append("Increase content snippet length for better context")
        
        if "Low relevance score" in issues:
            recommendations.append("Review query-document matching algorithm")
        
        return recommendations

# Global instances
legal_formatter = LegalFormatter()
citation_validator = CitationValidator()