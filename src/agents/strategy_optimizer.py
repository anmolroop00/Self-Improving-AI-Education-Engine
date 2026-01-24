"""Strategy Optimizer Agent.

Responsible for:
- Querying RAG for performance history
- Suggesting strategy changes based on trends
- Implementing A/B testing for content variations
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Type
from uuid import uuid4

from pydantic import BaseModel, Field

from .base_agent import BaseAgent
from .performance_analyst import PerformanceAnalysisOutput
from ..rag.schemas import ContentStrategy, Platform, ScriptStyle, StrategyChange


class StrategyRecommendation(BaseModel):
    """A recommended strategy change."""
    change_type: str = Field(description="What to change: timing, hashtags, style, hooks")
    current_value: str = Field(description="Current setting")
    recommended_value: str = Field(description="Recommended new setting")
    expected_impact: str = Field(description="Expected improvement")
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(description="Why this change is recommended")
    priority: int = Field(ge=1, le=5, description="1=highest priority, 5=lowest")


class StrategyOptimizationOutput(BaseModel):
    """Structured output for strategy optimization."""
    current_strategy_summary: str = Field(description="Summary of current strategy")
    performance_summary: str = Field(description="Recent performance overview")
    
    recommendations: List[StrategyRecommendation] = Field(
        description="Ordered list of strategy recommendations"
    )
    
    should_start_ab_test: bool = Field(description="Whether to start a new A/B test")
    ab_test_proposal: Optional[str] = Field(
        default=None,
        description="If should_start_ab_test, what to test"
    )
    
    urgent_changes: List[str] = Field(
        description="Changes that should be made immediately"
    )
    
    overall_strategy_health: str = Field(
        description="Assessment: healthy, needs_tuning, needs_major_changes"
    )


class StrategyOptimizerAgent(BaseAgent[StrategyOptimizationOutput]):
    """Agent that optimizes content strategy based on performance.
    
    Analyzes performance data and recommends changes to:
    - Posting times
    - Hashtag strategy
    - Script style
    - Engagement hooks
    """
    
    @property
    def agent_name(self) -> str:
        return "Strategy Optimizer"
    
    @property
    def system_prompt(self) -> str:
        return """You are an expert social media growth strategist.
Your task is to optimize content strategy based on performance data.

OPTIMIZATION PHILOSOPHY:
- Make data-driven decisions
- Change one thing at a time when possible
- Give changes time to show results (at least 7 videos)
- Use A/B testing for uncertain changes
- Don't over-optimize - sometimes simple is best

AREAS TO OPTIMIZE:
1. POSTING TIMES: When does the audience engage most?
2. HASHTAGS: Which drive discovery vs. which are noise?
3. SCRIPT STYLE: Storytelling vs. direct vs. question-based
4. HOOKS: What opening lines capture attention?
5. CONTENT TOPICS: Which AI topics resonate most?

THRESHOLD TRIGGERS:
- Engagement rate < 2%: Urgent content review needed
- Watch percentage < 50%: Videos not holding attention
- Views declining 3+ videos: Distribution strategy needs work
- Comments low: Call-to-action needed

RECOMMENDATION PRIORITIES:
1. Urgent fixes for clear problems
2. Quick wins with high confidence
3. A/B tests for uncertain improvements
4. Long-term experiments

A/B TESTING GUIDELINES:
- Test one variable at a time
- Run for 5-10 videos minimum
- Define success metrics upfront
- Document learnings regardless of outcome"""

    @property
    def output_schema(self) -> Type[StrategyOptimizationOutput]:
        return StrategyOptimizationOutput
    
    def optimize_strategy(
        self,
        analysis: PerformanceAnalysisOutput,
    ) -> StrategyOptimizationOutput:
        """Generate strategy optimization recommendations.
        
        Args:
            analysis: Performance analysis from PerformanceAnalystAgent
            
        Returns:
            StrategyOptimizationOutput with recommendations
        """
        # Get current strategy
        current_strategy = self.memory.get_active_strategy()
        
        context = {
            "performance_analysis": analysis.model_dump(),
            "current_strategy": current_strategy.model_dump() if current_strategy else None,
        }
        
        strategy_summary = "Default strategy (no customization yet)"
        if current_strategy:
            strategy_summary = f"""
Current posting times: {current_strategy.posting_times}
Current script style: {current_strategy.current_script_style.value}
Primary hashtags: {current_strategy.primary_hashtags}
A/B test active: {current_strategy.ab_test_active}"""

        prompt = f"""Analyze this performance data and current strategy, then recommend optimizations:

CURRENT STRATEGY:
{strategy_summary}

PERFORMANCE DATA:
- Videos analyzed: {analysis.videos_analyzed}
- Average views: {analysis.avg_views:.0f}
- Engagement rate: {analysis.avg_engagement_rate:.2%}
- Watch percentage: {analysis.avg_watch_percentage:.0%}

TOP INSIGHTS:
{chr(10).join(f'- {i.finding}: {i.recommendation}' for i in analysis.insights[:5])}

BEST PERFORMERS:
- Hashtags: {', '.join(analysis.best_performing_hashtags[:5])}
- Posting times: {analysis.best_posting_times}
- Content style: {analysis.best_content_style}

AREAS TO IMPROVE:
{chr(10).join(f'- {area}' for area in analysis.areas_to_improve)}

What strategy changes should be made? Prioritize recommendations by expected impact."""

        return self.generate_sync(prompt, context)
    
    def apply_recommendations(
        self,
        recommendations: List[StrategyRecommendation],
        apply_priority_threshold: int = 2,
    ) -> ContentStrategy:
        """Apply high-priority recommendations to strategy.
        
        Args:
            recommendations: List of recommendations to consider
            apply_priority_threshold: Apply recommendations at or below this priority
            
        Returns:
            Updated ContentStrategy
        """
        # Get or create strategy
        strategy = self.memory.get_active_strategy()
        if not strategy:
            strategy = ContentStrategy(id=str(uuid4()))
        
        for rec in recommendations:
            if rec.priority > apply_priority_threshold:
                continue
            
            # Normalize change_type to match StrategyChange schema
            change_type_map = {
                "timing": "posting_time",
                "hashtags": "hashtags",
                "style": "script_style",
                "hooks": "engagement_hooks",
                "content": "script_style",  # Map content to script_style
                "ab_test": "ab_test",
            }
            normalized_type = change_type_map.get(
                rec.change_type.lower(), 
                "script_style"  # Default fallback
            )
            
            # Record the change
            change = StrategyChange(
                id=str(uuid4()),
                change_type=normalized_type,
                previous_value=rec.current_value,
                new_value=rec.recommended_value,
                reason=rec.rationale,
                expected_impact=rec.expected_impact,
            )
            self.memory.save_strategy_change(change)
            
            # Apply the change
            self._apply_single_change(strategy, rec)
        
        # Save updated strategy
        strategy.id = str(uuid4())  # New version
        self.memory.save_strategy(strategy)
        
        return strategy
    
    def _apply_single_change(
        self,
        strategy: ContentStrategy,
        recommendation: StrategyRecommendation,
    ) -> None:
        """Apply a single recommendation to the strategy.
        
        Args:
            strategy: Strategy to modify
            recommendation: Recommendation to apply
        """
        if recommendation.change_type == "timing":
            # Parse and update posting times
            try:
                times = json.loads(recommendation.recommended_value)
                strategy.posting_times.update(times)
            except json.JSONDecodeError:
                pass
                
        elif recommendation.change_type == "hashtags":
            # Update hashtag lists
            try:
                hashtags = json.loads(recommendation.recommended_value)
                if isinstance(hashtags, dict):
                    strategy.primary_hashtags.update(hashtags)
            except json.JSONDecodeError:
                pass
                
        elif recommendation.change_type == "style":
            # Update script style
            style_map = {
                "storytelling": ScriptStyle.STORYTELLING,
                "direct": ScriptStyle.DIRECT,
                "question_based": ScriptStyle.QUESTION_BASED,
                "analogy_driven": ScriptStyle.ANALOGY_DRIVEN,
            }
            new_style = style_map.get(recommendation.recommended_value.lower())
            if new_style:
                strategy.current_script_style = new_style
                
        elif recommendation.change_type == "hooks":
            # Add new hooks to the list
            try:
                new_hooks = json.loads(recommendation.recommended_value)
                if isinstance(new_hooks, list):
                    strategy.engagement_hooks.extend(new_hooks)
                    strategy.engagement_hooks = strategy.engagement_hooks[:10]  # Keep top 10
            except json.JSONDecodeError:
                strategy.engagement_hooks.insert(0, recommendation.recommended_value)
    
    def setup_ab_test(
        self,
        test_variable: str,
        variant_a: str,
        variant_b: str,
    ) -> ContentStrategy:
        """Set up an A/B test in the strategy.
        
        Args:
            test_variable: What we're testing (timing, style, hashtags)
            variant_a: First variant description
            variant_b: Second variant description
            
        Returns:
            Updated ContentStrategy with A/B test active
        """
        strategy = self.memory.get_active_strategy()
        if not strategy:
            strategy = ContentStrategy(id=str(uuid4()))
        
        strategy.ab_test_active = True
        strategy.ab_test_variants = {
            "variable": test_variable,
            "variant_a": variant_a,
            "variant_b": variant_b,
            "started_at": datetime.now().isoformat(),
            "videos_in_a": 0,
            "videos_in_b": 0,
        }
        
        strategy.id = str(uuid4())
        self.memory.save_strategy(strategy)
        
        return strategy
