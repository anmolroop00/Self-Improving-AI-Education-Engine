"""Pydantic schemas for RAG memory structures.

These models define the structure of data stored in ChromaDB collections
for curriculum planning, performance tracking, and strategy optimization.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class Platform(str, Enum):
    """Supported social media platforms."""
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"


class ScriptStyle(str, Enum):
    """Content script styles for A/B testing."""
    STORYTELLING = "storytelling"
    DIRECT = "direct"
    QUESTION_BASED = "question_based"
    ANALOGY_DRIVEN = "analogy_driven"


class TopicPlan(BaseModel):
    """A curriculum plan for a main AI topic.
    
    Example: For "Regression", this might contain 10-15 subtopics
    progressing from basic concepts to practical applications.
    """
    id: str = Field(description="Unique identifier for the topic plan")
    main_topic: str = Field(description="Main topic name, e.g., 'Regression'")
    description: str = Field(description="Brief description of what will be covered")
    subtopics: List[str] = Field(
        description="Ordered list of subtopics/lessons",
        examples=[
            "What is regression? A simple introduction",
            "Linear regression: Drawing a line through points",
            "Why regression helps us make predictions"
        ]
    )
    current_index: int = Field(default=0, description="Index of next lesson to teach")
    total_lessons: int = Field(description="Total number of planned lessons")
    created_at: datetime = Field(default_factory=datetime.now)
    completed: bool = Field(default=False)
    
    @property
    def progress_percentage(self) -> float:
        """Calculate curriculum completion percentage."""
        if self.total_lessons == 0:
            return 0.0
        return (self.current_index / self.total_lessons) * 100
    
    @property
    def current_subtopic(self) -> Optional[str]:
        """Get the current subtopic to teach."""
        if self.current_index < len(self.subtopics):
            return self.subtopics[self.current_index]
        return None


class LessonContent(BaseModel):
    """Generated content for a single lesson/video.
    
    This represents the output of the content generation pipeline.
    """
    id: str = Field(description="Unique lesson identifier")
    topic_plan_id: str = Field(description="Reference to parent TopicPlan")
    subtopic: str = Field(description="The specific subtopic being taught")
    lesson_number: int = Field(description="Lesson number in the sequence")
    
    # Generated content
    raw_script: str = Field(description="Original script from Script Writer")
    clean_script: str = Field(description="Sanitized script for TTS")
    video_prompts: List[str] = Field(
        description="Veo 3 prompts for video segments",
        default_factory=list
    )
    
    # Metadata
    word_count: int = Field(description="Word count of clean script")
    estimated_duration: float = Field(description="Estimated audio duration in seconds")
    created_at: datetime = Field(default_factory=datetime.now)
    
    # Output files
    audio_path: Optional[str] = Field(default=None)
    video_paths: List[str] = Field(default_factory=list)
    final_video_path: Optional[str] = Field(default=None)
    thumbnail_path: Optional[str] = Field(default=None, description="AI-generated thumbnail")
    
    # Optimized metadata for publishing
    youtube_title: Optional[str] = Field(default=None)
    youtube_description: Optional[str] = Field(default=None)
    youtube_hashtags: List[str] = Field(default_factory=list)
    instagram_caption: Optional[str] = Field(default=None)
    instagram_hashtags: List[str] = Field(default_factory=list)


class VideoPerformance(BaseModel):
    """Performance analytics for a published video.
    
    Collected from YouTube Analytics and Instagram Insights.
    """
    id: str = Field(description="Unique performance record ID")
    lesson_id: str = Field(description="Reference to LessonContent")
    platform: Platform = Field(description="Platform where video was posted")
    platform_video_id: str = Field(description="Platform-specific video ID")
    
    # Core metrics
    views: int = Field(default=0)
    likes: int = Field(default=0)
    comments: int = Field(default=0)
    shares: int = Field(default=0)
    
    # Engagement metrics
    watch_time_seconds: float = Field(default=0.0, description="Total watch time")
    avg_watch_percentage: float = Field(
        default=0.0, 
        description="Average percentage of video watched"
    )
    engagement_rate: float = Field(
        default=0.0,
        description="(likes + comments + shares) / views"
    )
    
    # Demographics (age group -> percentage)
    demographics_age: Dict[str, float] = Field(
        default_factory=dict,
        description="Age distribution of viewers",
        examples=[{"18-24": 0.3, "25-34": 0.4, "35-44": 0.2, "45+": 0.1}]
    )
    
    # Geographic data (country -> percentage)
    demographics_geo: Dict[str, float] = Field(
        default_factory=dict,
        description="Geographic distribution",
        examples=[{"IN": 0.5, "US": 0.2, "UK": 0.1}]
    )
    
    # Content metadata for analysis
    hashtags_used: List[str] = Field(default_factory=list)
    post_time: datetime = Field(description="When the video was posted")
    post_day_of_week: str = Field(description="Day of week posted")
    script_style: ScriptStyle = Field(default=ScriptStyle.STORYTELLING)
    
    # Timestamps
    collected_at: datetime = Field(default_factory=datetime.now)
    
    def calculate_engagement_rate(self) -> float:
        """Calculate and update engagement rate."""
        if self.views == 0:
            return 0.0
        self.engagement_rate = (self.likes + self.comments + self.shares) / self.views
        return self.engagement_rate


class HashtagPerformance(BaseModel):
    """Track hashtag effectiveness across videos.
    
    Used by Strategy Optimizer to recommend best hashtags.
    """
    hashtag: str = Field(description="The hashtag without # symbol")
    platform: Platform
    times_used: int = Field(default=0)
    
    # Aggregated performance when this hashtag was used
    total_views: int = Field(default=0)
    total_engagement: int = Field(default=0)
    avg_engagement_rate: float = Field(default=0.0)
    
    # Effectiveness score (calculated by Strategy Optimizer)
    effectiveness_score: float = Field(
        default=0.0,
        description="0-100 score based on performance correlation"
    )
    
    last_used: datetime = Field(default_factory=datetime.now)
    
    def update_stats(self, views: int, engagement: int) -> None:
        """Update running statistics with new video data."""
        self.times_used += 1
        self.total_views += views
        self.total_engagement += engagement
        if self.total_views > 0:
            self.avg_engagement_rate = self.total_engagement / self.total_views
        self.last_used = datetime.now()


class PostingTimeSlot(BaseModel):
    """Performance data for a specific posting time slot."""
    day_of_week: str = Field(description="Monday, Tuesday, etc.")
    hour: int = Field(ge=0, le=23, description="Hour in 24h format")
    platform: Platform
    
    # Aggregated stats
    videos_posted: int = Field(default=0)
    avg_views: float = Field(default=0.0)
    avg_engagement_rate: float = Field(default=0.0)
    
    # Calculated score
    performance_score: float = Field(default=0.0)


class ContentStrategy(BaseModel):
    """Current content strategy configuration.
    
    Updated by Strategy Optimizer based on performance analysis.
    """
    id: str = Field(description="Strategy version identifier")
    created_at: datetime = Field(default_factory=datetime.now)
    active: bool = Field(default=True)
    
    # Posting schedule
    posting_times: Dict[str, str] = Field(
        description="Platform -> time mapping",
        examples=[{"youtube": "10:00", "instagram": "18:00"}]
    )
    best_days: Dict[str, List[str]] = Field(
        description="Platform -> best days to post",
        default_factory=lambda: {
            "youtube": ["Monday", "Wednesday", "Friday"],
            "instagram": ["Tuesday", "Thursday", "Saturday"]
        }
    )
    
    # Hashtag strategy
    primary_hashtags: Dict[str, List[str]] = Field(
        description="Platform -> always-use hashtags",
        default_factory=lambda: {
            "youtube": ["#AI", "#MachineLearning", "#LearnAI"],
            "instagram": ["#AI", "#TechEducation", "#LearnWithAI"]
        }
    )
    rotating_hashtags: Dict[str, List[str]] = Field(
        description="Platform -> hashtags to test",
        default_factory=dict
    )
    
    # Content style
    current_script_style: ScriptStyle = Field(default=ScriptStyle.STORYTELLING)
    engagement_hooks: List[str] = Field(
        description="Opening hooks that have performed well",
        default_factory=lambda: [
            "Did you know that...",
            "Imagine if you could...",
            "Let me show you something amazing..."
        ]
    )
    
    # A/B testing
    ab_test_active: bool = Field(default=False)
    ab_test_variants: Dict[str, str] = Field(
        description="Variant name -> description",
        default_factory=dict
    )
    
    # Performance thresholds for strategy changes
    min_engagement_rate: float = Field(
        default=0.02,
        description="Trigger strategy review if below this"
    )
    min_avg_watch_percentage: float = Field(
        default=0.5,
        description="Trigger content review if below this"
    )


class StrategyChange(BaseModel):
    """Record of a strategy modification.
    
    Maintains history of what was changed and why.
    """
    id: str = Field(description="Change record ID")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    change_type: Literal[
        "posting_time",
        "hashtags", 
        "script_style",
        "engagement_hooks",
        "ab_test"
    ]
    
    previous_value: str = Field(description="JSON string of previous value")
    new_value: str = Field(description="JSON string of new value")
    
    reason: str = Field(description="Why this change was made")
    expected_impact: str = Field(description="What improvement is expected")
    
    # Track if change was beneficial
    measured_impact: Optional[float] = Field(
        default=None,
        description="Actual impact after change (if measured)"
    )
