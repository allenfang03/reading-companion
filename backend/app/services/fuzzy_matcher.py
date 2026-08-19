from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein
import re
from typing import List, Tuple, Optional
from app.config import settings


class FuzzyMatcher:
    """Service for fuzzy text matching using rapidfuzz."""
    
    def __init__(self, threshold: int = None):
        self.threshold = threshold or settings.fuzzy_match_threshold
    
    def normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        # Lowercase
        text = text.lower()
        # Collapse whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def find_matches(
        self, 
        snippet: str, 
        full_text: str, 
        min_score: int = None
    ) -> List[dict]:
        """
        Find matches of snippet in full_text.
        
        Uses direct search first, then fuzzy matching as fallback.
        Returns list of matches with 'offset', 'score', 'matched_text'.
        """
        threshold = min_score or self.threshold
        snippet_normalized = self.normalize_text(snippet)
        snippet_len = len(snippet_normalized)
        
        matches = []
        
        # Fast path: Try direct substring search first
        full_text_lower = full_text.lower()
        
        # Try exact match
        pos = full_text_lower.find(snippet_normalized)
        if pos != -1:
            return [{
                'offset': pos,
                'score': 100,
                'matched_text': full_text[pos:pos + len(snippet_normalized)],
                'window_size': len(snippet_normalized)
            }]
        
        # Try with normalized whitespace differences (collapse multiple spaces to single)
        snippet_collapsed = ' '.join(snippet_normalized.split())
        
        # Sliding window search with reasonable window sizes
        # Limit search to reasonable sizes to avoid timeout
        window_min = max(int(snippet_len * 0.8), 10)
        window_max = min(int(snippet_len * 1.2), snippet_len + 200)
        
        max_searches = 10000  # Limit searches to prevent timeout
        
        search_count = 0
        for window_size in range(window_min, window_max + 1):
            if search_count > max_searches:
                break
            for i in range(0, len(full_text) - window_size + 1, max(1, window_size // 10)):
                search_count += 1
                if search_count > max_searches:
                    break
                    
                window_text = self.normalize_text(full_text[i:i + window_size])
                
                # Use token_sort_ratio for better handling of word reordering
                score = fuzz.token_sort_ratio(snippet_normalized, window_text)
                
                if score >= threshold:
                    matches.append({
                        'offset': i,
                        'score': score,
                        'matched_text': full_text[i:i + window_size],
                        'window_size': window_size
                    })
        
        # Sort by score descending, then by offset
        matches.sort(key=lambda m: (-m['score'], m['offset']))
        
        return matches[:10]  # Return top 10 matches only
    
    def is_ambiguous(
        self, 
        matches: List[dict], 
        score_diff_threshold: int = 5
    ) -> Tuple[bool, List[dict]]:
        """
        Check if matches are ambiguous (top 2 are too close in score).
        
        Returns (is_ambiguous, top_matches).
        """
        if len(matches) < 2:
            return False, matches[:1] if matches else []
        
        # Check if top 2 matches are within threshold of each other
        top_matches = matches[:2]
        if abs(top_matches[0]['score'] - top_matches[1]['score']) <= score_diff_threshold:
            return True, top_matches
        
        return False, [matches[0]]
    
    def get_best_match(
        self, 
        matches: List[dict]
    ) -> Optional[dict]:
        """Get the best match if one clearly stands out."""
        if not matches:
            return None
        
        is_amb, top = self.is_ambiguous(matches)
        if is_amb:
            return None  # Multiple good matches
        
        return top[0] if top else None


def resolve_offset_to_chapter(
    global_offset: int, 
    chapters: List[dict]
) -> Tuple[int, int]:
    """
    Resolve a global character offset to chapter_index and offset within chapter.
    
    Args:
        global_offset: Character offset in concatenated text
        chapters: List of dicts with 'char_count' keys in order
    
    Returns:
        (chapter_index, offset_within_chapter)
    """
    cumulative = 0
    
    for i, chapter in enumerate(chapters):
        char_count = chapter['char_count']
        
        if global_offset < cumulative + char_count:
            return i, global_offset - cumulative
        
        cumulative += char_count
    
    # If offset is at or past the end, return last chapter
    return len(chapters) - 1, chapters[-1]['char_count'] if chapters else 0
