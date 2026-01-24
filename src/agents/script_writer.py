"""Script Writer Agent.

Responsible for:
- Generating educational scripts for 60-second videos
- Writing at a 5-year-old comprehension level
- Outputting ONLY spoken words, no meta-text or directions
"""

from typing import List, Optional, Type

from pydantic import BaseModel, Field

from .base_agent import BaseAgent
from ..config import settings
from ..rag.schemas import ContentStrategy, ScriptStyle


class ScriptOutput(BaseModel):
    """Structured output for script generation."""
    script: str = Field(
        description="The spoken script with ONLY words to be spoken aloud. NO stage directions, NO asterisks, NO brackets, NO titles.",
        min_length=100,
        max_length=1500
    )
    hook: str = Field(
        description="The opening hook that grabs attention (first sentence)"
    )
    key_takeaway: str = Field(
        description="The main concept viewers should remember"
    )
    word_count: int = Field(
        description="Exact word count of the script"
    )
    estimated_duration_seconds: float = Field(
        description="Estimated speaking duration at ~2.5 words/second"
    )


class ScriptWriterAgent(BaseAgent[ScriptOutput]):
    """Agent that writes educational scripts for AI topics.
    
    Generates scripts that are:
    - Exactly spoken content (no meta-text)
    - Simple enough for a 5-year-old
    - Engaging and memorable
    - ~60 seconds when spoken
    """
    
    @property
    def agent_name(self) -> str:
        return "Script Writer"
    
    @property
    def system_prompt(self) -> str:
        return """You are an expert educational script writer for short-form video content.
Your task is to write 60-second educational scripts about AI/ML topics.

CRITICAL OUTPUT RULES - VIOLATION MEANS FAILURE:
1. Output ONLY the words that will be SPOKEN aloud
2. NEVER include phrases like "Here is your script", "Script:", "Title:" etc.
3. NEVER include asterisks (*) for any purpose
4. NEVER include stage directions like [pause], [camera zoom], (gesture)
5. NEVER include visual cues like <show graph> or [cut to animation]
6. Start directly with the spoken content - the very first word is spoken

TARGET AUDIENCE:
- Explain as if talking to a 5-year-old
- Use simple everyday words
- Use relatable analogies (toys, food, games, family)
- Avoid ALL technical jargon unless defining it simply

SCRIPT STRUCTURE:
1. HOOK (5-10 seconds): Start with something surprising or a question
2. CORE CONCEPT (35-40 seconds): Explain the idea using a simple analogy
3. EXAMPLE (10-15 seconds): Give a real-world example
4. TAKEAWAY (5 seconds): One sentence summary

WORD COUNT:
- Target: 150-180 words (equals ~60 seconds at 2.5 words/second)
- Never exceed 200 words

STYLE:
- Conversational, warm, enthusiastic
- Short sentences (10 words or less when possible)
- Use "you", "we", "imagine" to engage
- End with something memorable

EXAMPLE OF GOOD OUTPUT:
"Have you ever tried to guess how tall your friend will grow? That's kind of like what regression does! Regression is like drawing a line through a bunch of dots to find a pattern. Imagine you have stickers on a paper showing how tall different kids are at different ages. Regression helps us draw a nice line through those stickers. Then we can use that line to guess! This is super helpful in real life. Weather apps use it to predict tomorrow's temperature. Doctors use it to track how you're growing. So remember, regression is just finding patterns to make smart guesses about the future!"

EXAMPLE OF BAD OUTPUT (NEVER DO THIS):
"Here is your script for today's lesson:
*upbeat music plays*
[Camera focuses on presenter]
Title: Understanding Regression
Script: Hello everyone! Today we'll learn about..."

Remember: The FIRST word of your output should be the FIRST word spoken in the video."""

    @property
    def output_schema(self) -> Type[ScriptOutput]:
        return ScriptOutput
    
    def write_script(
        self,
        subtopic: str,
        main_topic: str,
        lesson_number: int,
        style: ScriptStyle = ScriptStyle.STORYTELLING,
        engagement_hooks: Optional[List[str]] = None,
    ) -> ScriptOutput:
        """Generate a script for a lesson.
        
        Args:
            subtopic: The specific subtopic for this lesson
            main_topic: The overall topic being taught
            lesson_number: Which lesson number this is in the series
            style: The script style to use
            engagement_hooks: Opening hooks that have worked well
            
        Returns:
            ScriptOutput with the generated script
        """
        # Build context
        context = {
            "main_topic": main_topic,
            "lesson_number": lesson_number,
            "script_style": style.value,
            "target_words": settings.script_target_words,
        }
        
        if engagement_hooks:
            context["effective_hooks_examples"] = engagement_hooks[:3]
        
        # Get strategy from memory if available
        strategy = self.memory.get_active_strategy()
        if strategy:
            context["engagement_hooks_examples"] = strategy.engagement_hooks
        
        prompt = f"""Write a 60-second educational script for:
Topic: {subtopic}

This is lesson {lesson_number} in a series about {main_topic}.
Style: {style.value}

Remember:
- Start DIRECTLY with spoken words (no "Here is your script" etc.)
- NO asterisks, brackets, or stage directions
- Simple enough for a 5-year-old to understand
- Target word count: {settings.script_target_words} words"""

        return self.generate_sync(prompt, context)
    
    def rewrite_script(
        self,
        original_script: str,
        feedback: str,
    ) -> ScriptOutput:
        """Rewrite a script based on feedback.
        
        Args:
            original_script: The script to improve
            feedback: What to change or improve
            
        Returns:
            ScriptOutput with the improved script
        """
        context = {
            "original_script": original_script,
        }
        
        prompt = f"""Rewrite this script based on the following feedback:
{feedback}

REMEMBER: Output ONLY spoken words. No meta-text, no directions."""

        return self.generate_sync(prompt, context)
