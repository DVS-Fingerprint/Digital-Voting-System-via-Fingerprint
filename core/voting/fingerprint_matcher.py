import hashlib
import base64
from typing import Optional, Tuple, List
from .models import FingerprintTemplate, Voter
from difflib import SequenceMatcher

class FingerprintMatcher:
    """Similarity-based fingerprint matching system"""
    
    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
    
    def calculate_template_similarity(self, template1: str, template2: str) -> float:
        """
        Calculate similarity between two fingerprint templates
        Returns a value between 0.0 (no similarity) and 1.0 (exact match)
        """
        try:
            # Method 1: String similarity (for hex templates)
            string_similarity = SequenceMatcher(None, template1, template2).ratio()
            
            # Method 2: Hash-based similarity
            hash1 = hashlib.md5(template1.encode()).hexdigest()
            hash2 = hashlib.md5(template2.encode()).hexdigest()
            hash_similarity = self._calculate_hash_similarity(hash1, hash2)
            
            # Method 3: Length-based similarity
            len1, len2 = len(template1), len(template2)
            length_similarity = 1.0 - abs(len1 - len2) / max(len1, len2)
            
            # Weighted average of all methods
            final_similarity = (
                string_similarity * 0.5 +
                hash_similarity * 0.3 +
                length_similarity * 0.2
            )
            
            return min(1.0, max(0.0, final_similarity))
            
        except Exception as e:
            print(f"Error calculating similarity: {e}")
            return 0.0
    
    def _calculate_hash_similarity(self, hash1: str, hash2: str) -> float:
        """Calculate similarity between two hash strings"""
        if len(hash1) != len(hash2):
            return 0.0
        
        matching_chars = sum(1 for a, b in zip(hash1, hash2) if a == b)
        return matching_chars / len(hash1)
    
    def find_best_match(self, input_template: str) -> Optional[Tuple[Voter, float]]:
        """
        Find the best matching voter for a given fingerprint template
        Returns (voter, confidence_score) or None if no match found
        """
        try:
            stored_templates = FingerprintTemplate.objects.select_related('voter').all()
            best_match = None
            best_score = 0.0
            
            for stored_template in stored_templates:
                similarity = self.calculate_template_similarity(
                    input_template, 
                    stored_template.template_hex
                )
                
                if similarity > self.similarity_threshold and similarity > best_score:
                    best_score = similarity
                    best_match = stored_template.voter
            
            if best_match:
                return (best_match, best_score)
            else:
                return None
                
        except Exception as e:
            print(f"Error in find_best_match: {e}")
            return None
    
    def find_multiple_matches(self, input_template: str, min_confidence: float = 0.7) -> List[Tuple[Voter, float]]:
        """
        Find all voters that match the input template above a minimum confidence
        Returns list of (voter, confidence_score) tuples
        """
        try:
            stored_templates = FingerprintTemplate.objects.select_related('voter').all()
            matches = []
            
            for stored_template in stored_templates:
                similarity = self.calculate_template_similarity(
                    input_template, 
                    stored_template.template_hex
                )
                
                if similarity >= min_confidence:
                    matches.append((stored_template.voter, similarity))
            
            # Sort by confidence (highest first)
            matches.sort(key=lambda x: x[1], reverse=True)
            return matches
            
        except Exception as e:
            print(f"Error in find_multiple_matches: {e}")
            return []
    
    def verify_fingerprint(self, input_template: str, expected_voter_id: int) -> Tuple[bool, float]:
        """
        Verify if input template matches a specific voter
        Returns (is_match, confidence_score)
        """
        try:
            expected_voter = Voter.objects.get(id=expected_voter_id)
            stored_templates = FingerprintTemplate.objects.filter(voter=expected_voter)
            
            best_score = 0.0
            for stored_template in stored_templates:
                similarity = self.calculate_template_similarity(
                    input_template, 
                    stored_template.template_hex
                )
                best_score = max(best_score, similarity)
            
            is_match = best_score >= self.similarity_threshold
            return (is_match, best_score)
            
        except Voter.DoesNotExist:
            return (False, 0.0)
        except Exception as e:
            print(f"Error in verify_fingerprint: {e}")
            return (False, 0.0)
    
    def get_template_statistics(self) -> dict:
        """Get statistics about stored templates"""
        try:
            total_templates = FingerprintTemplate.objects.count()
            total_voters = Voter.objects.count()
            templates_per_voter = total_templates / total_voters if total_voters > 0 else 0
            
            return {
                'total_templates': total_templates,
                'total_voters': total_voters,
                'templates_per_voter': round(templates_per_voter, 2),
                'similarity_threshold': self.similarity_threshold
            }
        except Exception as e:
            print(f"Error getting template statistics: {e}")
            return {}

# Global matcher instance
fingerprint_matcher = FingerprintMatcher(similarity_threshold=0.85) 