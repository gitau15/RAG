import re
from typing import Dict, List, Set, Optional, Any
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class DocumentType(Enum):
    LEGAL = "legal"
    COMMERCIAL = "commercial"
    TECHNICAL = "technical"
    FINANCIAL = "financial"
    GENERAL = "general"

class SensitivityLevel(Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"

class MetadataTagger:
    """Intelligent metadata tagging system"""
    
    def __init__(self):
        self.document_type_patterns = {
            DocumentType.LEGAL: [
                r'\b(court|judge|case|law|statute|regulation|precedent|jurisdiction)\b',
                r'\b(v\.|vs\.|versus|In\s+re|Ex\s+parte)\b',
                r'\b(Supreme\s+Court|District\s+Court|Circuit\s+Court)\b'
            ],
            DocumentType.COMMERCIAL: [
                r'\b(product|price|customer|client|sale|order|inventory|catalog)\b',
                r'\b(KES|USD|price|cost|discount|offer)\b',
                r'\b(commercial|business|enterprise|corporate)\b'
            ],
            DocumentType.TECHNICAL: [
                r'\b(technical|specification|documentation|API|code|system)\b',
                r'\b(version|release|update|patch|configuration)\b',
                r'\b(software|hardware|network|database|server)\b'
            ],
            DocumentType.FINANCIAL: [
                r'\b(financial|accounting|audit|budget|revenue|expense)\b',
                r'\b(balance\s+sheet|income\s+statement|cash\s+flow)\b',
                r'\b(KES|USD|shillings|dollars|million|billion)\b'
            ]
        }
        
        self.sensitivity_patterns = {
            SensitivityLevel.CONFIDENTIAL: [
                r'\b(confidential|proprietary|sensitive|classified)\b',
                r'\b(password|credential|key|secret)\b',
                r'\b(personal\s+data|PII|private\s+information)\b'
            ],
            SensitivityLevel.RESTRICTED: [
                r'\b(restricted|limited\s+distribution|internal\s+use)\b',
                r'\b(trade\s+secret|intellectual\s+property)\b'
            ]
        }
        
        self.industry_keywords = {
            'legal': ['law', 'court', 'case', 'jurisdiction', 'statute', 'regulation'],
            'healthcare': ['medical', 'patient', 'hospital', 'treatment', 'diagnosis'],
            'finance': ['banking', 'investment', 'loan', 'credit', 'insurance'],
            'technology': ['software', 'hardware', 'programming', 'development', 'IT'],
            'education': ['school', 'university', 'student', 'course', 'academic'],
            'government': ['ministry', 'department', 'regulation', 'policy', 'public']
        }
    
    def generate_document_metadata(self, content: str, filename: str, 
                                 tenant_id: str, user_id: str, 
                                 additional_tags: List[str] = None) -> Dict[str, Any]:
        """
        Generate comprehensive metadata for a document
        
        Args:
            content: Document content
            filename: Original filename
            tenant_id: Tenant identifier
            user_id: User identifier
            additional_tags: Additional tags to include
            
        Returns:
            Dictionary with document metadata
        """
        metadata = {
            'document_id': f"doc_{int(datetime.now().timestamp())}",
            'filename': filename,
            'file_extension': self._extract_file_extension(filename),
            'tenant_id': tenant_id,
            'uploaded_by': user_id,
            'upload_date': datetime.now().isoformat(),
            'content_length': len(content),
            'word_count': len(content.split()),
            'language': self._detect_language(content),
        }
        
        # Auto-detect document type
        document_type = self._classify_document_type(content)
        metadata['document_type'] = document_type.value
        
        # Auto-detect sensitivity level
        sensitivity = self._classify_sensitivity(content)
        metadata['sensitivity_level'] = sensitivity.value
        
        # Extract industries/sectors
        industries = self._extract_industries(content)
        metadata['industries'] = industries
        
        # Extract dates and time references
        dates = self._extract_dates(content)
        metadata['referenced_dates'] = dates
        
        # Extract key entities
        entities = self._extract_entities(content)
        metadata['entities'] = entities
        
        # Generate auto-tags
        auto_tags = self._generate_auto_tags(content, filename, document_type, industries)
        metadata['auto_tags'] = auto_tags
        
        # Combine with additional tags
        all_tags = list(set(auto_tags + (additional_tags or [])))
        metadata['tags'] = all_tags
        
        # Calculate document hash for integrity
        metadata['content_hash'] = self._calculate_content_hash(content)
        
        logger.info(f"Generated metadata for document: {filename}")
        return metadata
    
    def _extract_file_extension(self, filename: str) -> str:
        """Extract file extension from filename"""
        if '.' in filename:
            return filename.split('.')[-1].lower()
        return 'unknown'
    
    def _detect_language(self, content: str) -> str:
        """Basic language detection"""
        # Simple heuristic - could be enhanced with proper language detection library
        english_indicators = ['the', 'and', 'for', 'that', 'with', 'this', 'from', 'are']
        content_lower = content.lower()
        
        english_score = sum(1 for word in english_indicators if word in content_lower)
        
        if english_score > 3:
            return 'en'
        else:
            return 'unknown'
    
    def _classify_document_type(self, content: str) -> DocumentType:
        """Classify document type based on content analysis"""
        content_lower = content.lower()
        scores = {}
        
        for doc_type, patterns in self.document_type_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, content_lower, re.IGNORECASE))
                score += matches
            scores[doc_type] = score
        
        # Return type with highest score, default to GENERAL
        if any(scores.values()):
            return max(scores, key=scores.get)
        return DocumentType.GENERAL
    
    def _classify_sensitivity(self, content: str) -> SensitivityLevel:
        """Classify document sensitivity level"""
        content_lower = content.lower()
        
        # Check for explicit sensitivity indicators
        for level, patterns in self.sensitivity_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content_lower, re.IGNORECASE):
                    return level
        
        # Default classification based on document type
        doc_type = self._classify_document_type(content)
        if doc_type in [DocumentType.LEGAL, DocumentType.FINANCIAL]:
            return SensitivityLevel.INTERNAL
        else:
            return SensitivityLevel.PUBLIC
    
    def _extract_industries(self, content: str) -> List[str]:
        """Extract relevant industries/sectors"""
        content_lower = content.lower()
        industries = []
        
        for industry, keywords in self.industry_keywords.items():
            score = sum(1 for keyword in keywords if keyword in content_lower)
            if score >= 2:  # Require at least 2 keyword matches
                industries.append(industry)
        
        return industries
    
    def _extract_dates(self, content: str) -> List[str]:
        """Extract date references from content"""
        # Date patterns
        date_patterns = [
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',  # MM/DD/YYYY or DD/MM/YYYY
            r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b',    # YYYY-MM-DD
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b',  # Month DD, YYYY
            r'\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b'    # DD Month YYYY
        ]
        
        dates = []
        for pattern in date_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            dates.extend(matches)
        
        return list(set(dates))  # Remove duplicates
    
    def _extract_entities(self, content: str) -> Dict[str, List[str]]:
        """Extract named entities"""
        entities = {
            'organizations': [],
            'persons': [],
            'locations': [],
            'legal_citations': []
        }
        
        # Simple entity extraction patterns
        org_patterns = [
            r'\b(?:Inc|LLC|Ltd|Corporation|Company|Corp)\.?\b',
            r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b'  # Capitalized phrases (likely names)
        ]
        
        # Legal citation patterns
        legal_patterns = [
            r'\b(v\.|vs\.|versus)\b',
            r'\b\d+\s+(?:U\.S\.|F\.|S\. Ct\.|L\. Ed\.)\b'
        ]
        
        content_lower = content.lower()
        
        # Extract organizations (simplified)
        for pattern in org_patterns:
            matches = re.findall(pattern, content)
            entities['organizations'].extend(matches)
        
        # Extract legal citations
        for pattern in legal_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            entities['legal_citations'].extend(matches)
        
        # Remove duplicates and limit results
        for key in entities:
            entities[key] = list(set(entities[key]))[:10]  # Limit to 10 items
        
        return entities
    
    def _generate_auto_tags(self, content: str, filename: str, 
                          doc_type: DocumentType, industries: List[str]) -> List[str]:
        """Generate automatic tags based on content analysis"""
        tags = []
        
        # Add document type tag
        tags.append(doc_type.value)
        
        # Add industry tags
        tags.extend(industries)
        
        # Extract key terms from filename
        filename_terms = re.findall(r'[a-zA-Z]+', filename.lower())
        tags.extend(filename_terms[:3])  # First 3 terms from filename
        
        # Extract important content terms
        content_words = content.split()
        # Filter for longer, potentially important words
        important_words = [word for word in content_words 
                          if len(word) > 4 and word.isalpha()][:5]
        tags.extend(important_words)
        
        # Add sensitivity tags
        sensitivity = self._classify_sensitivity(content)
        if sensitivity != SensitivityLevel.PUBLIC:
            tags.append(f"sensitivity_{sensitivity.value}")
        
        # Remove duplicates and normalize
        unique_tags = list(set(tag.lower().replace(' ', '_') for tag in tags if tag))
        
        return unique_tags[:20]  # Limit to 20 tags
    
    def _calculate_content_hash(self, content: str) -> str:
        """Calculate content hash for integrity verification"""
        import hashlib
        return hashlib.md5(content.encode()).hexdigest()
    
    def enrich_metadata_with_context(self, metadata: Dict[str, Any], 
                                   context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich existing metadata with additional context
        
        Args:
            metadata: Existing metadata
            context: Additional context information
            
        Returns:
            Enriched metadata
        """
        enriched = metadata.copy()
        
        # Add context information
        if 'collection_name' in context:
            enriched['collection_context'] = context['collection_name']
        
        if 'processing_mode' in context:
            enriched['mode'] = context['processing_mode']
        
        if 'tenant_metadata' in context:
            enriched['tenant_info'] = context['tenant_metadata']
        
        # Add processing timestamps
        enriched['processed_at'] = datetime.now().isoformat()
        
        return enriched
    
    def validate_metadata_completeness(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate metadata completeness and quality
        
        Args:
            metadata: Metadata to validate
            
        Returns:
            Validation results
        """
        required_fields = ['document_id', 'filename', 'tenant_id', 'upload_date']
        missing_fields = [field for field in required_fields if field not in metadata]
        
        validation_result = {
            'complete': len(missing_fields) == 0,
            'missing_fields': missing_fields,
            'quality_score': self._calculate_metadata_quality(metadata),
            'recommendations': []
        }
        
        # Generate recommendations
        if 'tags' not in metadata or len(metadata.get('tags', [])) < 3:
            validation_result['recommendations'].append("Add more descriptive tags")
        
        if 'document_type' not in metadata:
            validation_result['recommendations'].append("Classify document type")
        
        if metadata.get('sensitivity_level') == SensitivityLevel.RESTRICTED.value:
            validation_result['recommendations'].append("Ensure proper access controls")
        
        return validation_result
    
    def _calculate_metadata_quality(self, metadata: Dict[str, Any]) -> float:
        """Calculate metadata quality score (0-1)"""
        score = 0.0
        total_checks = 8.0
        
        # Check presence of key fields
        if 'document_id' in metadata:
            score += 1
        if 'filename' in metadata:
            score += 1
        if 'tenant_id' in metadata:
            score += 1
        if 'upload_date' in metadata:
            score += 1
        
        # Check quality of populated fields
        if metadata.get('tags') and len(metadata['tags']) >= 3:
            score += 1
        if metadata.get('document_type'):
            score += 1
        if metadata.get('content_length', 0) > 0:
            score += 1
        if metadata.get('language'):
            score += 1
        
        return score / total_checks

# Global instance
metadata_tagger = MetadataTagger()