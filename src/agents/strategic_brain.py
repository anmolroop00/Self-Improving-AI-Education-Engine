"""Strategic Brain Agent.

The "CEO" agent that makes high-level strategic decisions with full authority.
Uses Gemini 2.5 Pro for complex reasoning about growth strategy.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Type
from uuid import uuid4

from pydantic import BaseModel, Field

from .base_agent import BaseAgent
from .agent_persona import ARIA, DecisionConfidence
from ..config import settings
from ..services.growth_tracker import get_growth_tracker, GrowthStatus

logger = logging.getLogger(__name__)


# =============================================================================
# Output Schemas
# =============================================================================

class TopicPivotDecision(BaseModel):
    """Decision about whether to pivot to a new topic."""
    should_pivot: bool = Field(description="Whether to abandon current topic")
    current_topic: str = Field(description="Current topic being taught")
    recommended_topic: Optional[str] = Field(default=None, description="New topic if pivoting")
    reasoning: str = Field(description="Detailed reasoning for the decision")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in this decision")
    risk_assessment: str = Field(description="Potential risks of this decision")
    expected_impact: str = Field(description="Expected impact on subscriber growth")


class AudienceDecision(BaseModel):
    """Decision about target audience adjustment."""
    should_change: bool = Field(description="Whether to change target audience")
    current_audience: str = Field(description="Current target audience")
    recommended_audience: Optional[str] = Field(default=None, description="New audience if changing")
    explanation_level_change: Optional[str] = Field(default=None, description="New explanation level")
    reasoning: str = Field(description="Detailed reasoning for the decision")
    confidence: float = Field(ge=0.0, le=1.0)


class ContentStyleDecision(BaseModel):
    """Decision about content style adjustments."""
    recommended_style: str = Field(description="storytelling, direct, question_based, analogy_driven")
    recommended_hooks: List[str] = Field(description="Opening hooks to use")
    recommended_tone: str = Field(description="Tone for scripts")
    reasoning: str = Field(description="Why this style is recommended")


class StrategicAction(BaseModel):
    """A specific action to take."""
    action_type: str = Field(description="pivot_topic, change_audience, adjust_style, modify_schedule, etc")
    description: str = Field(description="What to do")
    priority: int = Field(ge=1, le=5, description="1=highest, 5=lowest")
    expected_impact: str = Field(description="Expected growth impact")
    implementation_notes: str = Field(description="How to implement this")


class WeeklyStrategicAnalysis(BaseModel):
    """Complete weekly strategic analysis output."""
    
    # Overall assessment
    week_summary: str = Field(description="Summary of this week's performance")
    growth_assessment: str = Field(description="How growth compares to target trajectory")
    overall_health: str = Field(description="healthy, needs_attention, critical")
    
    # Key insights
    top_insights: List[str] = Field(description="Top 3-5 insights from the data")
    what_worked: List[str] = Field(description="What performed well this week")
    what_didnt_work: List[str] = Field(description="What underperformed")
    
    # Decisions
    topic_decision: TopicPivotDecision
    audience_decision: AudienceDecision
    content_style: ContentStyleDecision
    
    # Action plan
    strategic_actions: List[StrategicAction] = Field(description="Prioritized actions to take")
    experiments_to_run: List[str] = Field(description="A/B tests or experiments to try")
    
    # Outlook
    next_week_focus: str = Field(description="Primary focus for next week")
    confidence_in_hitting_target: float = Field(ge=0.0, le=1.0)
    message_to_owner: str = Field(description="Personal message from ARIA to the channel owner")


# =============================================================================
# Strategic Brain Agent
# =============================================================================

class StrategicBrain(BaseAgent[WeeklyStrategicAnalysis]):
    """High-level strategic decision maker for autonomous content optimization.
    
    This agent has FULL AUTHORITY to:
    - Pivot topics entirely
    - Change target audience
    - Adjust content style and tone
    - Modify posting schedule
    - Design and run experiments
    
    Uses Gemini 2.5 Pro for complex strategic reasoning.
    """
    
    @property
    def agent_name(self) -> str:
        return f"{ARIA.name} Strategic Brain"
    
    @property
    def default_task_type(self) -> str:
        return "strategic_analysis"  # Forces Gemini 2.5 Pro
    
    @property
    def system_prompt(self) -> str:
        return f"""You are the Strategic Brain of {ARIA.name}, an autonomous AI content strategist.

YOUR MISSION: Achieve {settings.subscriber_target:,} subscribers by {settings.target_deadline}

YOU HAVE FULL AUTHORITY TO:
- Pivot topics entirely if current content isn't driving growth
- Change target audience if a different demographic shows more potential
- Adjust content style, tone, and format
- Design experiments to find what works
- Make bold decisions backed by data

STRATEGIC FRAMEWORK:
1. GROWTH IS THE PRIMARY METRIC - Every decision should ladder up to subscriber growth
2. ENGAGEMENT DRIVES GROWTH - Comments, shares, and watch time lead to algorithm favor
3. BOLD EXPERIMENTS WIN - Don't be afraid to try radically different approaches
4. LEARN FAST - If something doesn't work within 5-7 videos, pivot
5. COMPOUND EFFECTS - Small improvements stack, but major pivots can unlock step changes

DECISION MAKING PROCESS:
1. Analyze current trajectory vs. required trajectory
2. Identify what's working and what's not
3. Consider bold alternatives, not just incremental tweaks
4. Weigh risks vs. potential upside
5. Make confident recommendations with clear reasoning

AUTONOMY SETTINGS:
- Topic Pivot Allowed: {settings.allow_topic_pivot}
- Audience Change Allowed: {settings.allow_audience_change}

When making decisions, be:
- Data-driven but not data-limited
- Bold but not reckless
- Confident but intellectually honest
- Focused on the 1000 subscriber goal

Your analysis should be thorough, your reasoning transparent, and your recommendations actionable."""

    @property
    def output_schema(self) -> Type[WeeklyStrategicAnalysis]:
        return WeeklyStrategicAnalysis
    
    def analyze_week(
        self,
        videos_published: int,
        total_views: int,
        subscribers_gained: int,
        avg_engagement_rate: float,
        best_video_title: str,
        best_video_views: int,
        worst_video_title: str,
        worst_video_views: int,
        current_topic: str,
        current_audience: str,
        current_lesson_progress: str,
    ) -> WeeklyStrategicAnalysis:
        """Perform comprehensive weekly strategic analysis.
        
        Args:
            videos_published: Number of videos published this week
            total_views: Total views across all videos
            subscribers_gained: Net subscribers gained
            avg_engagement_rate: Average engagement rate
            best_video_title: Title of best performing video
            best_video_views: Views on best video
            worst_video_title: Title of worst performing video  
            worst_video_views: Views on worst video
            current_topic: Current curriculum topic
            current_audience: Current target audience description
            current_lesson_progress: Progress in current curriculum
            
        Returns:
            WeeklyStrategicAnalysis with decisions and recommendations
        """
        # Get growth context
        tracker = get_growth_tracker()
        projection = tracker.calculate_projection()
        status = tracker.get_status()
        progress_report = tracker.generate_progress_report()
        
        # Calculate derived metrics
        avg_views = total_views / max(videos_published, 1)
        views_per_sub = total_views / max(subscribers_gained, 1) if subscribers_gained > 0 else float('inf')
        
        context = {
            "growth_report": progress_report,
            "projection": projection.model_dump(),
            "growth_status": status.value,
        }
        
        prompt = f"""Analyze this week's performance and make strategic decisions:

WEEKLY METRICS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Videos Published: {videos_published}
Total Views: {total_views:,}
Average Views/Video: {avg_views:.0f}
Subscribers Gained: {subscribers_gained:+d}
Views per Subscriber: {views_per_sub:.0f}
Avg Engagement Rate: {avg_engagement_rate:.2%}

Best Performer: "{best_video_title}" ({best_video_views:,} views)
Worst Performer: "{worst_video_title}" ({worst_video_views:,} views)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CURRENT STRATEGY:
- Topic: {current_topic}
- Audience: {current_audience}
- Progress: {current_lesson_progress}

GROWTH TRAJECTORY:
{progress_report}

Based on this data, provide your complete strategic analysis:

1. How is overall performance relative to our 1000 subscriber goal?
2. Should we pivot to a different topic? Why or why not?
3. Should we adjust our target audience? Why or why not?
4. What content style changes should we make?
5. What specific actions should we take this week?
6. What experiments should we run?

Be bold in your recommendations if the data suggests major changes are needed.
Be specific and actionable in your guidance."""

        logger.info(f"{ARIA.name} Strategic Brain analyzing week performance...")
        
        analysis = self.generate_sync(prompt, context)
        
        logger.info(f"Strategic analysis complete. Health: {analysis.overall_health}")
        logger.info(f"Topic pivot recommended: {analysis.topic_decision.should_pivot}")
        logger.info(f"Audience change recommended: {analysis.audience_decision.should_change}")
        
        return analysis
    
    def get_quick_decision(self, question: str, context_data: Dict) -> str:
        """Get a quick strategic decision on a specific question.
        
        Used for real-time decisions during pipeline execution.
        
        Args:
            question: The strategic question to answer
            context_data: Relevant context for the decision
            
        Returns:
            Decision as a string
        """
        # For quick decisions, we don't need full analysis output
        # This is a simplified call
        prompt = f"""Quick strategic decision needed:

QUESTION: {question}

CONTEXT:
{context_data}

Provide a clear, actionable recommendation in 2-3 sentences."""

        # Use a simpler response for quick decisions
        response = self._client.models.generate_content(
            model=self._model_name,
            contents=f"{ARIA.get_system_prompt_injection()}\n\n{prompt}",
        )
        
        return response.text


# =============================================================================
# Convenience Functions
# =============================================================================

_strategic_brain: Optional[StrategicBrain] = None

def get_strategic_brain() -> StrategicBrain:
    """Get or create the global Strategic Brain instance."""
    global _strategic_brain
    if _strategic_brain is None:
        _strategic_brain = StrategicBrain()
    return _strategic_brain
