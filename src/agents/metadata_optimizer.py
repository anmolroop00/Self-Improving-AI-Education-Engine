"""Metadata Optimizer Agent.

Responsible for:
- Generating optimized video titles for maximum reach
- Creating platform-specific hashtag strategies
- Crafting compelling descriptions
- Optimizing for YouTube and Instagram algorithms
"""

from typing import List, Optional, Type
from pydantic import BaseModel, Field

from .base_agent import BaseAgent
from ..config import settings
from ..rag.schemas import Platform


class VideoMetadata(BaseModel):
    """Optimized metadata for a video."""
    
    # Title variations
    youtube_title: str = Field(
        description="Optimized title for YouTube (max 100 chars, includes keywords)",
        max_length=100
    )
    instagram_caption_title: str = Field(
        description="Short attention-grabbing title for Instagram caption start",
        max_length=50
    )
    
    # Descriptions
    youtube_description: str = Field(
        description="Full YouTube description with keywords, timestamps, and CTAs"
    )
    instagram_caption: str = Field(
        description="Instagram caption with emojis and hashtags integrated"
    )
    
    # Hashtags
    youtube_hashtags: List[str] = Field(
        description="3-5 relevant hashtags for YouTube (no # prefix)",
        min_length=3,
        max_length=5
    )
    instagram_hashtags: List[str] = Field(
        description="20-30 optimized hashtags for Instagram reach",
        min_length=15,
        max_length=30
    )
    
    # SEO Keywords
    primary_keywords: List[str] = Field(
        description="Primary keywords to target for discoverability"
    )
    
    # Engagement hooks
    hook_question: str = Field(
        description="Question to ask in comments to boost engagement"
    )
    call_to_action: str = Field(
        description="Clear CTA for the end of description"
    )


class MetadataOptimizerAgent(BaseAgent[VideoMetadata]):
    """Agent that generates optimized metadata for maximum reach.
    
    Uses performance data from RAG memory to:
    - Identify high-performing hashtag patterns
    - Craft titles that drive clicks
    - Write descriptions that boost discoverability
    """
    
    @property
    def agent_name(self) -> str:
        return "Metadata Optimizer"
    
    @property
    def system_prompt(self) -> str:
        return """You are an expert social media optimizer specializing in educational content on YouTube and Instagram.

Your goal is to maximize video reach and engagement through strategic metadata optimization.

TITLE OPTIMIZATION RULES:
1. YouTube titles: Start with power words (How, Why, What, The Truth About)
2. Include the main topic keyword early in the title
3. Create curiosity gap without being clickbait
4. Keep it under 60 characters for mobile display
5. Use numbers when relevant (e.g., "3 Ways AI Learns")

HASHTAG STRATEGY:

For YouTube (3-5 hashtags):
- Use broad topic hashtags (#AI, #MachineLearning, #Tech)
- Include specific topic hashtag (#NeuralNetworks)
- Add educational hashtag (#LearnAI, #AIExplained)

For Instagram (20-30 hashtags):
- Mix of large (1M+ posts), medium (100K-1M), and small (10K-100K) hashtags
- Include:
  * Niche hashtags: #AIForBeginners #MLExplained
  * Broad tech: #ArtificialIntelligence #TechEducation
  * Educational: #LearnSomethingNew #EducationalContent
  * Trending: Check for current AI/tech trends
  * Community: #AIcommunity #TechTok #LearnOnInstagram
  * Content type: #Reels #AIReels #TechReels #Shorts

DESCRIPTION OPTIMIZATION:
1. First 2 lines are crucial (shown in preview)
2. Include main keyword in first sentence
3. Add timestamps for longer content
4. Include relevant links and CTAs
5. End with engagement question

ENGAGEMENT BOOSTERS:
- Ask a question to encourage comments
- Use "Save this for later" prompts
- Include "Follow for more" CTAs
- Create FOMO ("Don't miss the next video")

PLATFORM-SPECIFIC NOTES:
- YouTube: Focus on searchability and watch time
- Instagram: Focus on saves, shares, and hashtag reach"""

    @property
    def output_schema(self) -> Type[VideoMetadata]:
        return VideoMetadata
    
    def optimize_metadata(
        self,
        topic: str,
        subtopic: str,
        script_summary: str,
        lesson_number: int,
    ) -> VideoMetadata:
        """Generate optimized metadata for a video.
        
        Args:
            topic: Main topic of the curriculum
            subtopic: Specific lesson topic
            script_summary: Brief summary or key takeaway from script
            lesson_number: Which lesson in the series
            
        Returns:
            VideoMetadata with all optimized fields
        """
        # Get top performing hashtags from memory
        top_youtube_hashtags = self.memory.get_top_hashtags(Platform.YOUTUBE, limit=10)
        top_instagram_hashtags = self.memory.get_top_hashtags(Platform.INSTAGRAM, limit=20)
        
        context = {
            "main_topic": topic,
            "subtopic": subtopic,
            "lesson_number": lesson_number,
            "script_summary": script_summary,
        }
        
        # Add historical performance data if available
        if top_youtube_hashtags:
            context["proven_youtube_hashtags"] = [h.hashtag for h in top_youtube_hashtags[:5]]
        if top_instagram_hashtags:
            context["proven_instagram_hashtags"] = [h.hashtag for h in top_instagram_hashtags[:10]]
        
        prompt = f"""Generate optimized metadata for this educational video:

Topic: {topic}
Lesson: {subtopic} (Lesson #{lesson_number})
Key Takeaway: {script_summary}

Target Audience: General public, beginners interested in AI/ML, explained simply.

Create:
1. Compelling YouTube title (max 100 chars, keyword-rich)
2. Instagram caption title (short, attention-grabbing)
3. Full YouTube description with timestamps placeholder
4. Instagram caption with emojis
5. YouTube hashtags (3-5, most relevant)
6. Instagram hashtags (20-30, mix of sizes for maximum reach)
7. Primary SEO keywords
8. Engagement question for comments
9. Clear call-to-action

Prioritize discoverability and engagement potential."""

        return self.generate_sync(prompt, context)
    
    def generate_trending_hashtags(
        self,
        platform: Platform,
        topic: str,
        count: int = 15,
    ) -> List[str]:
        """Generate trending hashtags for a specific platform and topic.
        
        Args:
            platform: Target platform
            topic: Topic to generate hashtags for
            count: Number of hashtags to generate
            
        Returns:
            List of hashtag strings (without # prefix)
        """
        # Get historical performance
        top_hashtags = self.memory.get_top_hashtags(platform, limit=20)
        proven = [h.hashtag for h in top_hashtags] if top_hashtags else []
        
        prompt = f"""Generate {count} optimized hashtags for {platform.value} about: {topic}

{'Previously successful hashtags to consider: ' + ', '.join(proven[:10]) if proven else ''}

Requirements:
- Return ONLY the hashtag words (no # symbol)
- Mix of popularity levels (some broad, some niche)
- Relevant to AI/ML education
- Currently trending or evergreen
- One hashtag per line"""

        # For simple list output, we'll use a direct call
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
        )
        
        # Parse response into list
        hashtags = []
        for line in response.text.strip().split("\n"):
            tag = line.strip().lstrip("#").strip()
            if tag and len(tag) > 1:
                hashtags.append(tag)
        
        return hashtags[:count]
    
    def create_ab_test_titles(
        self,
        topic: str,
        subtopic: str,
        variations: int = 3,
    ) -> List[str]:
        """Generate multiple title variations for A/B testing.
        
        Args:
            topic: Main topic
            subtopic: Specific lesson topic
            variations: Number of title variations
            
        Returns:
            List of title variations
        """
        prompt = f"""Generate {variations} different YouTube title variations for:
Topic: {topic}
Lesson: {subtopic}

Each title should:
- Be under 60 characters
- Use a different hook strategy
- Target the same audience (beginners)

Strategies to use:
1. Question-based ("What is...?")
2. Benefit-focused ("Learn X in 60 seconds")
3. Curiosity gap ("The truth about...")

Return one title per line."""

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
        )
        
        titles = [line.strip() for line in response.text.strip().split("\n") if line.strip()]
        return titles[:variations]
