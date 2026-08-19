import anthropic
from app.config import settings
from typing import Optional, List
import json


class LLMService:
    """Service for interacting with Anthropic Claude API."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.client = anthropic.Anthropic(
            api_key=api_key or settings.anthropic_api_key
        )
        self.timeout = settings.llm_timeout
        # Use claude-sonnet-5 (current stable model)
        self.model = "claude-sonnet-5"
    
    def is_available(self) -> bool:
        """Check if LLM service is properly configured."""
        return bool(self.client.api_key)
    
    async def extract_character_names(self, chapter_text: str) -> List[str]:
        """
        Extract character names from a chapter using the LLM.
        
        Returns a JSON array of character names.
        """
        if not self.is_available():
            return []
        
        prompt = f"""You are given a chapter from a novel. Extract all proper noun character names -- people who are characters in the story (not places, not organizations unless they're personified, not author names or dedications).

Return a JSON array of strings. Only include names that appear as proper nouns referring to characters. Do not include titles, nicknames, or aliases unless they are the primary way the character is referred to in this chapter.

Chapter text:
{chapter_text}"""
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
            timeout=self.timeout
        )
        
        text = response.content[0].text.strip()
        
        # Try to parse as JSON
        try:
            # Handle potential markdown code blocks
            if text.startswith('```'):
                text = text.split('```')[1]
                if text.startswith('json'):
                    text = text[4:]
            return json.loads(text.strip())
        except json.JSONDecodeError:
            # Fallback: try to extract names from text
            return self._extract_names_fallback(text)
    
    def _extract_names_fallback(self, text: str) -> List[str]:
        """Fallback extraction if JSON parsing fails."""
        import re
        # Try to find quoted strings
        matches = re.findall(r'"([^"]+)"', text)
        if matches:
            return matches
        # Try single quotes
        matches = re.findall(r"'([^']+)'", text)
        return matches
    
    async def generate_recap(
        self, 
        assembled_text: str, 
        estimated_tokens: int
    ) -> str:
        """
        Generate a recap of the given text.
        
        If estimated_tokens > 15000, use chunked summarization.
        """
        if not self.is_available():
            raise Exception("LLM service not available - no API key configured")
        
        if estimated_tokens <= 15000:
            return await self._single_pass_recap(assembled_text)
        else:
            return await self._chunked_recap(assembled_text)
    
    async def _single_pass_recap(self, text: str) -> str:
        """Single-pass summarization for shorter texts."""
        prompt = f"""You are a reading companion summarizing a novel for a reader who needs a quick recap.

Write 4-5 sentences summarizing the events in this passage. Focus on what happened and who was involved. Do not summarize the entire book -- only what occurs in this specific section.

Write in present tense, as if describing ongoing events. Keep it concise and in the reader's voice.

Passage:
{text}"""
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=settings.max_tokens_recap,
            messages=[{"role": "user", "content": prompt}],
            timeout=self.timeout
        )
        
        text = None
        for block in response.content:
            if hasattr(block, 'text') and block.text and getattr(block, 'type', None) == 'text':
                text = block.text
                break
        if not text:
            raise Exception("LLM returned no text content")
        
        return text.strip()
    
    async def _chunked_recap(self, text: str) -> str:
        """Chunked summarization for longer texts."""
        # Split into chunks of ~48,000 characters (~12,000 tokens)
        chunk_size = 48000
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        
        sub_summaries = []
        
        for chunk in chunks:
            prompt = f"""Summarize this section of a novel in 2-3 sentences. Focus on what happens.

Section:
{chunk}"""
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=settings.max_tokens_sub_recap,
                messages=[{"role": "user", "content": prompt}],
                timeout=self.timeout
            )
            sub_summaries.append(response.content[0].text.strip())
        
        # Combine sub-summaries
        combined = "\n\n".join(sub_summaries)
        
        final_prompt = f"""The following are summaries of consecutive sections of a chapter. Combine them into 4-5 coherent sentences.

{combined}"""
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=settings.max_tokens_recap,
            messages=[{"role": "user", "content": final_prompt}],
            timeout=self.timeout
        )
        
        text = None
        for block in response.content:
            if hasattr(block, 'text') and block.text and getattr(block, 'type', None) == 'text':
                text = block.text
                break
        if not text:
            raise Exception("LLM returned no text content")
        
        return text.strip()
    
    async def synthesize_character(
        self, 
        character_name: str, 
        snippets: List[str]
    ) -> str:
        """
        Synthesize a character description from mention snippets.
        """
        if not self.is_available():
            raise Exception("LLM service not available - no API key configured")
        
        # Limit to a reasonable number of snippets to avoid huge prompts
        # Sample evenly across all snippets if there are too many
        max_snippets = 15
        if len(snippets) > max_snippets:
            step = len(snippets) // max_snippets
            sampled = snippets[::step][:max_snippets]
        else:
            sampled = snippets
        
        # Truncate each snippet to keep prompt size manageable
        max_snippet_len = 200
        truncated = [s[:max_snippet_len] + "..." if len(s) > max_snippet_len else s for s in sampled]
        
        excerpts = "\n\n".join(f"<snippet_{i+1}>\n{s}" for i, s in enumerate(truncated))
        
        prompt = f"""You are given several excerpts from a novel, all mentioning "{character_name}". Based *only* on these excerpts, describe this character.

Output ONLY plain text in this exact format (no markdown, no asterisks, no bullet symbols):

Role: [One sentence about who this character is in the story]

Physical Description: [One sentence describing their appearance]

Personality Traits: [One sentence about their personality]

Relationships: [One sentence about their key relationships with others]

Do not invent or infer details not present in the excerpts. If you don't have information for a section, write "Not enough information in the excerpts."

Excerpts:
{excerpts}"""
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=600,  # Increased to prevent cutoff
            messages=[{"role": "user", "content": prompt}],
            timeout=self.timeout
        )
        
        # Extract text from response (skip thinking blocks)
        text = None
        for block in response.content:
            if hasattr(block, 'text') and block.text and getattr(block, 'type', None) == 'text':
                text = block.text
                break
        
        if not text:
            raise Exception(f"LLM returned no text content (stop_reason={response.stop_reason})")
        
        return text.strip()


# Singleton instance
llm_service = LLMService()
