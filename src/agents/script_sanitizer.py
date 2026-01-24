"""Script Sanitizer.

CRITICAL COMPONENT: Fixes the TTS issue by removing all non-spoken content.

This is the last line of defense before scripts go to TTS.
Even if the Script Writer makes mistakes, this sanitizer catches:
- "Here is your script" type phrases
- Asterisk-wrapped directions (*camera zooms*)
- Bracketed stage directions [pause]
- Angular bracket cues <show animation>
- Title/header lines
- Any other meta-text
"""

import re
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class SanitizerResult:
    """Result of script sanitization."""
    clean_script: str
    original_script: str
    issues_found: List[str]
    word_count: int
    estimated_duration: float  # seconds


class ScriptSanitizer:
    """Sanitizes scripts to contain ONLY spoken words.
    
    This class provides regex-based cleaning to ensure no meta-text,
    stage directions, or other non-spoken content survives to TTS.
    """
    
    # Patterns that indicate non-spoken content
    REMOVAL_PATTERNS: List[Tuple[str, str]] = [
        # "Here is your script" type intros
        (r"^here\s+(is|are)\s+(your\s+)?(the\s+)?script[:\s]*", "intro phrase"),
        (r"^(script|title|lesson|video)\s*[:\-]\s*", "label prefix"),
        
        # Asterisk-wrapped content (*camera direction*)
        (r"\*[^*]+\*", "asterisk direction"),
        
        # Bracket-wrapped content [stage direction]
        (r"\[[^\]]+\]", "bracket direction"),
        
        # Angular bracket content <visual cue>
        (r"<[^>]+>", "visual cue"),
        
        # Parenthetical directions (pause) (gesture)
        (r"\([^)]*(?:pause|gesture|music|sound|cut|fade|zoom|focus|camera|visual|animation|graphic|screen|display)[^)]*\)", "parenthetical direction"),
        
        # Common meta phrases
        (r"^(opening|intro|hook|conclusion|outro|end)\s*[:\-]?\s*", "section label"),
        (r"(?:^|\n)\s*(?:scene|shot|take)\s*\d*\s*[:\-]?\s*", "scene marker"),
        
        # Timestamps and durations
        (r"\(\d+[:\-]\d+\s*(?:seconds?|secs?|s)?\)", "timestamp"),
        (r"\[\d+[:\-]\d+\]", "timestamp"),
        
        # Speaker labels
        (r"^(?:narrator|host|speaker|voiceover|vo)\s*[:\-]\s*", "speaker label"),
        
        # Action lines often starting with verbs
        (r"^(?:cut to|fade to|transition to|show|display|pan to|zoom (?:in|out))[^\n]*\n?", "action line"),
        
        # Music/Sound cues
        (r"♪[^♪]*♪", "music notation"),
        (r"🎵[^🎵]*🎵", "music emoji"),
        (r"\((?:upbeat |background |soft )?music[^)]*\)", "music cue"),
        (r"\((?:sound effect|sfx)[^)]*\)", "sound effect"),
    ]
    
    # Multi-line patterns
    MULTILINE_REMOVAL_PATTERNS: List[Tuple[str, str]] = [
        # Script metadata blocks
        (r"^---+\s*\n.*?\n---+\s*\n", "metadata block"),
        (r"^title:.*?\n", "title line"),
        (r"^topic:.*?\n", "topic line"),
        (r"^duration:.*?\n", "duration line"),
    ]
    
    # Characters/sequences to clean up
    CLEANUP_PATTERNS: List[Tuple[str, str]] = [
        # Multiple newlines to single
        (r"\n{3,}", "\n\n"),
        # Multiple spaces to single
        (r"  +", " "),
        # Leading/trailing whitespace on lines
        (r"^\s+|\s+$", ""),
        # Orphaned punctuation
        (r"\s+([.,!?])", r"\1"),
    ]
    
    @classmethod
    def sanitize(cls, raw_script: str) -> SanitizerResult:
        """Remove all non-spoken content from a script.
        
        Args:
            raw_script: The original script text
            
        Returns:
            SanitizerResult with cleaned script and metadata
        """
        clean = raw_script
        issues: List[str] = []
        
        # Apply multiline patterns first
        for pattern, issue_name in cls.MULTILINE_REMOVAL_PATTERNS:
            if re.search(pattern, clean, re.IGNORECASE | re.MULTILINE):
                issues.append(f"Removed: {issue_name}")
                clean = re.sub(pattern, "", clean, flags=re.IGNORECASE | re.MULTILINE)
        
        # Apply single-line removal patterns
        for pattern, issue_name in cls.REMOVAL_PATTERNS:
            if re.search(pattern, clean, re.IGNORECASE | re.MULTILINE):
                issues.append(f"Removed: {issue_name}")
                clean = re.sub(pattern, "", clean, flags=re.IGNORECASE | re.MULTILINE)
        
        # Clean up whitespace and formatting
        for pattern, replacement in cls.CLEANUP_PATTERNS:
            clean = re.sub(pattern, replacement, clean, flags=re.MULTILINE)
        
        # Final trim
        clean = clean.strip()
        
        # Calculate metrics
        word_count = len(clean.split())
        estimated_duration = word_count / 2.5  # ~2.5 words per second
        
        return SanitizerResult(
            clean_script=clean,
            original_script=raw_script,
            issues_found=issues,
            word_count=word_count,
            estimated_duration=estimated_duration,
        )
    
    @classmethod
    def validate_clean(cls, script: str) -> Tuple[bool, List[str]]:
        """Validate that a script contains only spoken content.
        
        Args:
            script: The script to validate
            
        Returns:
            Tuple of (is_clean, list of issues found)
        """
        issues: List[str] = []
        
        # Check for remaining problematic patterns
        if "*" in script:
            issues.append("Contains asterisk (*) characters")
        if re.search(r"\[[^\]]+\]", script):
            issues.append("Contains bracketed content")
        if re.search(r"<[^>]+>", script):
            issues.append("Contains angular bracket content")
        if re.search(r"^here\s+is", script, re.IGNORECASE):
            issues.append("Starts with 'here is'")
        if re.search(r"^script\s*:", script, re.IGNORECASE):
            issues.append("Starts with 'script:'")
            
        return (len(issues) == 0, issues)
    
    @classmethod
    def quick_clean(cls, text: str) -> str:
        """Quick single-pass cleaning for simple cases.
        
        Args:
            text: Text to clean
            
        Returns:
            Cleaned text
        """
        # Remove common problematic patterns
        text = re.sub(r"\*[^*]+\*", "", text)  # *directions*
        text = re.sub(r"\[[^\]]+\]", "", text)  # [directions]
        text = re.sub(r"<[^>]+>", "", text)  # <directions>
        text = re.sub(r"^here\s+is\s+your\s+script[:\s]*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s+", " ", text)  # Normalize whitespace
        return text.strip()


def sanitize_script(raw_script: str) -> str:
    """Convenience function for quick script sanitization.
    
    Args:
        raw_script: The script to clean
        
    Returns:
        Clean script with only spoken content
    """
    result = ScriptSanitizer.sanitize(raw_script)
    return result.clean_script
