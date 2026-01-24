"""Performance Analyst Agent.

Responsible for:
- Fetching analytics from YouTube and Instagram APIs
- Identifying patterns in content performance
- Storing insights in RAG for strategy optimization
"""

from datetime import datetime
from typing import Dict, List, Optional, Type
from uuid import uuid4

from pydantic import BaseModel, Field

from .base_agent import BaseAgent
from ..rag.schemas import Platform, VideoPerformance


class PerformanceInsight(BaseModel):
    """A single insight derived from performance data."""
    insight_type: str = Field(description="Category: timing, hashtags, content, demographics")
    finding: str = Field(description="The specific finding or pattern")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in this insight")
    recommendation: str = Field(description="Actionable recommendation based on this insight")
    supporting_data: str = Field(description="Brief summary of data supporting this insight")


class PerformanceAnalysisOutput(BaseModel):
    """Structured output for performance analysis."""
    analysis_period: str = Field(description="Time period analyzed (e.g., 'last 30 days')")
    videos_analyzed: int = Field(description="Number of videos in analysis")
    
    # Key metrics
    avg_views: float = Field(description="Average views per video")
    avg_engagement_rate: float = Field(description="Average engagement rate")
    avg_watch_percentage: float = Field(description="Average % of video watched")
    
    # Insights
    insights: List[PerformanceInsight] = Field(description="Key insights from the analysis")
    
    # Top performers
    best_performing_hashtags: List[str] = Field(description="Hashtags that drive engagement")
    best_posting_times: Dict[str, str] = Field(description="Platform -> optimal posting time")
    best_content_style: str = Field(description="Script style that performs best")
    
    # Areas for improvement
    areas_to_improve: List[str] = Field(description="Specific aspects needing improvement")


class PerformanceAnalystAgent(BaseAgent[PerformanceAnalysisOutput]):
    """Agent that analyzes content performance and identifies patterns.
    
    Works with data from:
    - YouTube Analytics API
    - Instagram Insights API
    - Internal RAG memory
    """
    
    @property
    def agent_name(self) -> str:
        return "Performance Analyst"
    
    @property
    def system_prompt(self) -> str:
        return """You are an expert social media analytics specialist.
Your task is to analyze video performance data and extract actionable insights.

ANALYSIS AREAS:
1. TIMING: When do videos perform best? Day of week, time of day
2. HASHTAGS: Which hashtags correlate with better performance?
3. CONTENT: Which script styles, hooks, and topics resonate?
4. DEMOGRAPHICS: Who is the audience? What content do they prefer?
5. ENGAGEMENT: What drives likes, comments, shares?

INSIGHT QUALITY:
- Base insights on actual data patterns
- Provide specific, actionable recommendations
- Note confidence levels based on sample size
- Look for both successes and underperformance

METRICS TO CONSIDER:
- Views: Raw reach
- Watch time: Content quality indicator
- Engagement rate: (likes + comments + shares) / views
- Completion rate: How much video was watched
- Comment sentiment: What are viewers saying?

OUTPUT FOCUS:
- Prioritize insights that can directly improve strategy
- Be specific: "Post at 6PM IST" not "post in evening"
- Identify patterns, not just individual outliers
- Connect findings to actionable recommendations"""

    @property
    def output_schema(self) -> Type[PerformanceAnalysisOutput]:
        return PerformanceAnalysisOutput
    
    def analyze_performance(
        self,
        platform: Optional[Platform] = None,
        days: int = 30,
    ) -> PerformanceAnalysisOutput:
        """Analyze recent video performance.
        
        Args:
            platform: Specific platform to analyze, or None for both
            days: Number of days to look back
            
        Returns:
            PerformanceAnalysisOutput with insights and recommendations
        """
        # Gather performance data from memory
        performances: List[VideoPerformance] = []
        
        if platform:
            performances = self.memory.get_performance_history(platform, limit=50)
        else:
            for p in [Platform.YOUTUBE, Platform.INSTAGRAM]:
                performances.extend(self.memory.get_performance_history(p, limit=25))
        
        if not performances:
            # Return a default response when no data is available
            return PerformanceAnalysisOutput(
                analysis_period=f"last {days} days",
                videos_analyzed=0,
                avg_views=0,
                avg_engagement_rate=0,
                avg_watch_percentage=0,
                insights=[PerformanceInsight(
                    insight_type="data",
                    finding="No performance data available yet",
                    confidence=1.0,
                    recommendation="Publish videos to start gathering performance data",
                    supporting_data="0 videos in database"
                )],
                best_performing_hashtags=[],
                best_posting_times={},
                best_content_style="storytelling",
                areas_to_improve=["Start posting to gather data"]
            )
        
        # Prepare data summary for analysis
        data_summary = self._summarize_performance_data(performances)
        
        context = {
            "platform_filter": platform.value if platform else "all platforms",
            "analysis_period": f"{days} days",
            "data_summary": data_summary,
        }
        
        prompt = f"""Analyze the following video performance data and provide insights:

{data_summary}

Identify patterns in:
1. Best posting times
2. Most effective hashtags
3. Content styles that work
4. Audience demographics
5. Areas needing improvement

Be specific and actionable in your recommendations."""

        return self.generate_sync(prompt, context)
    
    def _summarize_performance_data(self, performances: List[VideoPerformance]) -> str:
        """Create a text summary of performance data for the LLM.
        
        Args:
            performances: List of VideoPerformance records
            
        Returns:
            Human-readable summary
        """
        if not performances:
            return "No performance data available."
        
        # Calculate aggregates
        total_views = sum(p.views for p in performances)
        avg_views = total_views / len(performances)
        avg_engagement = sum(p.engagement_rate for p in performances) / len(performances)
        avg_watch = sum(p.avg_watch_percentage for p in performances) / len(performances)
        
        # Group by day of week
        by_day: Dict[str, List[float]] = {}
        for p in performances:
            day = p.post_day_of_week
            if day not in by_day:
                by_day[day] = []
            by_day[day].append(p.views)
        
        # Collect hashtags
        hashtag_counts: Dict[str, int] = {}
        hashtag_views: Dict[str, int] = {}
        for p in performances:
            for tag in p.hashtags_used:
                hashtag_counts[tag] = hashtag_counts.get(tag, 0) + 1
                hashtag_views[tag] = hashtag_views.get(tag, 0) + p.views
        
        # Build summary
        summary = f"""
VIDEO PERFORMANCE SUMMARY
========================
Total videos analyzed: {len(performances)}
Total views: {total_views:,}
Average views per video: {avg_views:.0f}
Average engagement rate: {avg_engagement:.2%}
Average watch percentage: {avg_watch:.0%}

PERFORMANCE BY DAY:
"""
        for day, views in sorted(by_day.items(), key=lambda x: sum(x[1])/len(x[1]), reverse=True):
            avg = sum(views) / len(views)
            summary += f"- {day}: {avg:.0f} avg views ({len(views)} videos)\n"
        
        summary += "\nTOP HASHTAGS BY VIEWS:\n"
        top_hashtags = sorted(hashtag_views.items(), key=lambda x: x[1], reverse=True)[:10]
        for tag, views in top_hashtags:
            count = hashtag_counts[tag]
            summary += f"- #{tag}: {views:,} total views ({count} uses)\n"
        
        # Add some individual video data
        summary += "\nRECENT VIDEO PERFORMANCE:\n"
        for p in performances[:5]:
            summary += f"- {p.post_time.strftime('%Y-%m-%d %H:%M')}: {p.views:,} views, {p.engagement_rate:.2%} engagement, {p.platform.value}\n"
        
        return summary
    
    def identify_underperforming_patterns(self) -> List[str]:
        """Identify patterns in underperforming videos.
        
        Returns:
            List of patterns/issues found in poor performers
        """
        performances = self.memory.get_performance_history(limit=50)
        
        if len(performances) < 5:
            return ["Not enough data for pattern detection"]
        
        # Find videos below average
        avg_views = sum(p.views for p in performances) / len(performances)
        underperformers = [p for p in performances if p.views < avg_views * 0.5]
        
        patterns = []
        
        # Analyze common characteristics
        if underperformers:
            # Check timing
            times = [p.post_time.hour for p in underperformers]
            common_hour = max(set(times), key=times.count)
            patterns.append(f"Many underperformers posted around {common_hour}:00")
            
            # Check days
            days = [p.post_day_of_week for p in underperformers]
            common_day = max(set(days), key=days.count)
            patterns.append(f"Weak performance commonly on {common_day}")
        
        return patterns if patterns else ["No clear underperformance patterns detected"]
