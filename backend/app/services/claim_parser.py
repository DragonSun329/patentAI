"""Claim parser service - extract and analyze individual patent claims."""
import re
import uuid
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ParsedClaim:
    """Parsed individual claim."""
    claim_number: int
    claim_text: str
    is_independent: bool
    parent_claim_number: Optional[int]
    claim_type: Optional[str]


class ClaimParserService:
    """Parse patent claims text into individual structured claims."""
    
    # Pattern to match claim numbers (handles various formats)
    CLAIM_PATTERNS = [
        # "1. A method for..." or "1) A method for..."
        r'(?:^|\n)\s*(\d+)[.\)]\s*(.+?)(?=(?:\n\s*\d+[.\)]|\Z))',
        # "Claim 1: A method..." or "Claim 1. A method..."
        r'(?:^|\n)\s*[Cc]laim\s+(\d+)[.:]\s*(.+?)(?=(?:\n\s*[Cc]laim\s+\d+|\Z))',
    ]
    
    # Patterns indicating dependent claims
    DEPENDENCY_PATTERNS = [
        r'(?:according to|as (?:claimed|defined|set forth|recited) in|of) claim[s]?\s+(\d+)',
        r'claim[s]?\s+(\d+)[,\s]+(?:wherein|where|further|additionally)',
        r'(?:The|A|An)\s+\w+\s+(?:of|according to)\s+claim\s+(\d+)',
    ]
    
    # Claim type indicators
    CLAIM_TYPE_PATTERNS = {
        'method': r'^(?:A|The)\s+method',
        'apparatus': r'^(?:A|An|The)\s+(?:apparatus|device|machine|equipment)',
        'system': r'^(?:A|The)\s+system',
        'composition': r'^(?:A|The)\s+(?:composition|compound|formulation|mixture)',
        'article': r'^(?:A|An|The)\s+(?:article|product|manufacture)',
        'process': r'^(?:A|The)\s+process',
    }
    
    def parse_claims(self, claims_text: str) -> List[ParsedClaim]:
        """
        Parse raw claims text into structured individual claims.
        
        Args:
            claims_text: Full claims section text from patent
            
        Returns:
            List of ParsedClaim objects
        """
        if not claims_text:
            return []
        
        # Clean the text
        claims_text = self._preprocess(claims_text)
        
        # Try each pattern
        claims = []
        for pattern in self.CLAIM_PATTERNS:
            matches = re.findall(pattern, claims_text, re.DOTALL | re.MULTILINE)
            if matches:
                for claim_num_str, claim_text in matches:
                    claim_num = int(claim_num_str)
                    claim_text = self._clean_claim_text(claim_text)
                    
                    if claim_text and len(claim_text) > 10:  # Filter empty/trivial
                        is_independent, parent_num = self._analyze_dependency(claim_text)
                        claim_type = self._detect_claim_type(claim_text)
                        
                        claims.append(ParsedClaim(
                            claim_number=claim_num,
                            claim_text=claim_text,
                            is_independent=is_independent,
                            parent_claim_number=parent_num,
                            claim_type=claim_type
                        ))
                break
        
        # Fallback: split by numbered patterns if no matches
        if not claims:
            claims = self._fallback_parse(claims_text)
        
        # Sort by claim number
        claims.sort(key=lambda c: c.claim_number)
        
        return claims
    
    def _preprocess(self, text: str) -> str:
        """Preprocess claims text for parsing."""
        # Normalize whitespace
        text = re.sub(r'\r\n', '\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        # Remove page numbers/headers that might be in the text
        text = re.sub(r'\n\s*-?\d+-?\s*\n', '\n', text)
        return text.strip()
    
    def _clean_claim_text(self, text: str) -> str:
        """Clean individual claim text."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _analyze_dependency(self, claim_text: str) -> Tuple[bool, Optional[int]]:
        """
        Analyze if claim is independent or dependent.
        
        Returns:
            Tuple of (is_independent, parent_claim_number)
        """
        for pattern in self.DEPENDENCY_PATTERNS:
            match = re.search(pattern, claim_text, re.IGNORECASE)
            if match:
                parent_num = int(match.group(1))
                return (False, parent_num)
        
        # If no dependency reference found, it's independent
        return (True, None)
    
    def _detect_claim_type(self, claim_text: str) -> Optional[str]:
        """Detect the type of claim (method, apparatus, etc.)."""
        for claim_type, pattern in self.CLAIM_TYPE_PATTERNS.items():
            if re.match(pattern, claim_text, re.IGNORECASE):
                return claim_type
        return None
    
    def _fallback_parse(self, claims_text: str) -> List[ParsedClaim]:
        """Fallback parsing for non-standard claim formats."""
        claims = []
        
        # Split by lines and look for numbered items
        lines = claims_text.split('\n')
        current_claim = []
        current_num = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if line starts a new claim
            num_match = re.match(r'^(\d+)[.\)]\s*(.*)$', line)
            
            if num_match:
                # Save previous claim
                if current_num is not None and current_claim:
                    full_text = ' '.join(current_claim)
                    is_independent, parent_num = self._analyze_dependency(full_text)
                    claim_type = self._detect_claim_type(full_text)
                    claims.append(ParsedClaim(
                        claim_number=current_num,
                        claim_text=full_text,
                        is_independent=is_independent,
                        parent_claim_number=parent_num,
                        claim_type=claim_type
                    ))
                
                # Start new claim
                current_num = int(num_match.group(1))
                current_claim = [num_match.group(2)] if num_match.group(2) else []
            elif current_num is not None:
                # Continue current claim
                current_claim.append(line)
        
        # Don't forget the last claim
        if current_num is not None and current_claim:
            full_text = ' '.join(current_claim)
            is_independent, parent_num = self._analyze_dependency(full_text)
            claim_type = self._detect_claim_type(full_text)
            claims.append(ParsedClaim(
                claim_number=current_num,
                claim_text=full_text,
                is_independent=is_independent,
                parent_claim_number=parent_num,
                claim_type=claim_type
            ))
        
        return claims
    
    def extract_key_elements(self, claim_text: str) -> List[str]:
        """
        Extract key technical elements/components from a claim.
        Useful for comparison highlighting.
        """
        elements = []
        
        # Extract things in quotes
        quoted = re.findall(r'"([^"]+)"', claim_text)
        elements.extend(quoted)
        
        # Extract noun phrases after "comprising", "including", "having"
        comprising_match = re.search(
            r'(?:comprising|including|having|consists? of)[:\s]+(.+?)(?:wherein|where|;|$)',
            claim_text,
            re.IGNORECASE
        )
        if comprising_match:
            components = comprising_match.group(1)
            # Split by common delimiters
            parts = re.split(r'[;,](?:\s*and)?|\s+and\s+', components)
            for part in parts:
                part = part.strip()
                # Extract the main noun phrase (simplified)
                noun_match = re.search(r'(?:a|an|the)?\s*(\w+(?:\s+\w+){0,3})', part, re.IGNORECASE)
                if noun_match and len(noun_match.group(1)) > 3:
                    elements.append(noun_match.group(1).strip())
        
        return list(set(elements))[:10]  # Dedupe and limit


# Singleton instance
claim_parser = ClaimParserService()
