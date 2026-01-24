"""Orchestrator Agent.

The main coordinator that runs the entire video production pipeline:
1. Gets next lesson from curriculum
2. Generates script and sanitizes it
3. Creates video prompts
4. Triggers TTS and video generation
5. Composes final video
6. Publishes to platforms
7. Collects analytics and optimizes strategy
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from ..config import settings
from ..rag.memory_store import MemoryStore
from ..rag.schemas import ContentStrategy, LessonContent, Platform, TopicPlan

from .curriculum_planner import CurriculumPlannerAgent
from .script_writer import ScriptWriterAgent
from .script_sanitizer import ScriptSanitizer
from .video_prompt_engineer import VideoPromptEngineerAgent
from .performance_analyst import PerformanceAnalystAgent
from .strategy_optimizer import StrategyOptimizerAgent
from .metadata_optimizer import MetadataOptimizerAgent

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Result of a pipeline run."""
    success: bool
    lesson: Optional[LessonContent]
    error: Optional[str] = None
    stage_reached: str = "init"
    final_video_path: Optional[Path] = None


class Orchestrator:
    """Main orchestrator that coordinates all agents and production pipeline.
    
    Implements the daily workflow:
    1. Check curriculum for next lesson
    2. Generate content (script, video prompts)
    3. Produce video (TTS, video generation, composition)
    4. Publish to platforms
    5. Analyze and optimize
    """
    
    def __init__(self, memory: Optional[MemoryStore] = None):
        """Initialize the orchestrator with all agents.
        
        Args:
            memory: Shared memory store. Creates new instance if None.
        """
        self.memory = memory or MemoryStore()
        
        # Initialize all agents with shared memory
        self.curriculum_planner = CurriculumPlannerAgent(memory=self.memory)
        self.script_writer = ScriptWriterAgent(memory=self.memory)
        self.video_prompt_engineer = VideoPromptEngineerAgent(memory=self.memory)
        self.performance_analyst = PerformanceAnalystAgent(memory=self.memory)
        self.strategy_optimizer = StrategyOptimizerAgent(memory=self.memory)
        self.metadata_optimizer = MetadataOptimizerAgent(memory=self.memory)
        
        # Ensure output directories exist
        settings.ensure_directories()
        
        logger.info("Orchestrator initialized with all agents")
    
    def run_daily_pipeline(
        self,
        topic: Optional[str] = None,
        dry_run: bool = False,
    ) -> PipelineResult:
        """Run the complete daily content pipeline.
        
        Args:
            topic: Specific topic to use. If None, continues current curriculum.
            dry_run: If True, generate content but don't produce video or publish.
            
        Returns:
            PipelineResult with status and generated content
        """
        logger.info(f"Starting daily pipeline (dry_run={dry_run})")
        
        try:
            # Step 1: Get or create curriculum
            lesson_info = self._get_next_lesson(topic)
            if not lesson_info:
                return PipelineResult(
                    success=False,
                    lesson=None,
                    error="No lesson available",
                    stage_reached="curriculum"
                )
            
            plan, subtopic = lesson_info
            logger.info(f"Lesson: {subtopic} (#{plan.current_index + 1} of {plan.total_lessons})")
            
            # Step 2: Generate script
            script_output = self._generate_script(plan, subtopic)
            logger.info(f"Script generated: {script_output.word_count} words")
            
            # Step 3: Sanitize script (FIX FOR TTS ISSUE)
            sanitized = ScriptSanitizer.sanitize(script_output.script)
            if sanitized.issues_found:
                logger.warning(f"Script sanitization: {sanitized.issues_found}")
            
            logger.info(f"Script sanitized: {sanitized.word_count} words, ~{sanitized.estimated_duration:.0f}s")
            
            # Step 4: Generate video prompts
            video_prompts = self.video_prompt_engineer.create_prompts(
                script=sanitized.clean_script,
                topic=plan.main_topic,
                subtopic=subtopic,
                aspect_ratio="9:16",  # Default to vertical for Shorts/Reels
                target_duration=settings.video_target_duration,
            )
            logger.info(f"Generated {video_prompts.total_segments} video segments")
            
            # Create lesson content record
            lesson = LessonContent(
                id=str(uuid4()),
                topic_plan_id=plan.id,
                subtopic=subtopic,
                lesson_number=plan.current_index + 1,
                raw_script=script_output.script,
                clean_script=sanitized.clean_script,
                video_prompts=[seg.veo_prompt for seg in video_prompts.segments],
                word_count=sanitized.word_count,
                estimated_duration=sanitized.estimated_duration,
            )
            
            # Save lesson to memory
            self.memory.save_lesson(lesson)
            
            if dry_run:
                logger.info("Dry run complete - skipping video production and publishing")
                return PipelineResult(
                    success=True,
                    lesson=lesson,
                    stage_reached="content_generation"
                )
            
            # Step 5: Produce video (TTS + Veo 3 + Composition)
            final_video = self._produce_video(lesson)
            if final_video:
                lesson.final_video_path = str(final_video)
                self.memory.save_lesson(lesson)
            
            # Step 5.5: Generate thumbnail (if feature enabled)
            thumbnail_path = None
            if settings.features.thumbnails:
                logger.info("Generating AI thumbnail...")
                try:
                    from ..production.thumbnail_generator import ThumbnailGenerator
                    thumbnail_gen = ThumbnailGenerator()
                    thumbnail_path = thumbnail_gen.generate_from_lesson(
                        title=subtopic,
                        topic=plan.main_topic,
                        lesson_number=plan.current_index + 1,
                        script_summary=script_output.key_takeaway,
                    )
                    lesson.thumbnail_path = str(thumbnail_path)
                    logger.info(f"Thumbnail generated: {thumbnail_path}")
                except Exception as e:
                    logger.warning(f"Thumbnail generation failed: {e}")
            
            # Step 6: Generate optimized metadata (titles, hashtags, descriptions)
            logger.info("Generating optimized metadata for maximum reach...")
            metadata = self.metadata_optimizer.optimize_metadata(
                topic=plan.main_topic,
                subtopic=subtopic,
                script_summary=script_output.key_takeaway,
                lesson_number=plan.current_index + 1,
            )
            
            logger.info(f"YouTube Title: {metadata.youtube_title}")
            logger.info(f"Instagram Hashtags: {len(metadata.instagram_hashtags)} tags")
            logger.info(f"YouTube Hashtags: {metadata.youtube_hashtags}")
            
            # Store metadata with lesson
            lesson.youtube_title = metadata.youtube_title
            lesson.youtube_description = metadata.youtube_description
            lesson.youtube_hashtags = metadata.youtube_hashtags
            lesson.instagram_caption = metadata.instagram_caption
            lesson.instagram_hashtags = metadata.instagram_hashtags
            self.memory.save_lesson(lesson)
            
            # Step 7: Publish to platforms
            # (Implementation in platforms module)
            
            # Step 8: Mark lesson complete
            self.curriculum_planner.mark_lesson_complete(plan.id)
            
            return PipelineResult(
                success=True,
                lesson=lesson,
                stage_reached="complete",
                final_video_path=final_video
            )
            
        except Exception as e:
            logger.exception(f"Pipeline failed: {e}")
            return PipelineResult(
                success=False,
                lesson=None,
                error=str(e),
                stage_reached="error"
            )
    
    def _get_next_lesson(self, topic: Optional[str]) -> Optional[tuple[TopicPlan, str]]:
        """Get the next lesson to produce.
        
        Args:
            topic: Specific topic, or None to use current curriculum
            
        Returns:
            Tuple of (TopicPlan, subtopic) or None
        """
        if topic:
            # Create new curriculum for this topic
            plan = self.curriculum_planner.plan_curriculum(topic)
            return (plan, plan.current_subtopic) if plan.current_subtopic else None
        
        # Try to get next lesson from existing curriculum
        return self.curriculum_planner.get_next_lesson()
    
    def _generate_script(self, plan: TopicPlan, subtopic: str):
        """Generate script for the lesson.
        
        Args:
            plan: The topic plan
            subtopic: Specific subtopic for this lesson
            
        Returns:
            ScriptOutput from the script writer
        """
        from ..rag.schemas import ScriptStyle
        
        # Get current strategy for style and hooks
        strategy = self.memory.get_active_strategy()
        
        # Use strategy settings or defaults
        style = strategy.current_script_style if strategy else ScriptStyle.STORYTELLING
        hooks = strategy.engagement_hooks if strategy else None
        
        return self.script_writer.write_script(
            subtopic=subtopic,
            main_topic=plan.main_topic,
            lesson_number=plan.current_index + 1,
            style=style,
            engagement_hooks=hooks,
        )
    
    def _produce_video(self, lesson: LessonContent) -> Optional[Path]:
        """Produce the final video.
        
        Args:
            lesson: Lesson content with script and prompts
            
        Returns:
            Path to final video, or None if failed
        """
        from ..production.tts_service import TTSService
        from ..production.video_generator import VideoGenerator
        from ..production.video_composer import VideoComposer
        from uuid import uuid4
        
        try:
            # Step 1: Generate TTS audio
            logger.info("Generating TTS audio...")
            tts = TTSService.create()
            audio_path = settings.audio_output_dir / f"lesson_{lesson.lesson_number}_{uuid4().hex[:8]}.mp3"
            
            tts.synthesize(lesson.clean_script, audio_path)
            audio_duration = tts.get_audio_duration(audio_path)
            logger.info(f"Audio generated: {audio_path} ({audio_duration:.1f}s)")
            
            # Step 2: Generate video clips with Veo 3
            logger.info("Generating video clips with Veo 3...")
            video_gen = VideoGenerator()
            video_clips = video_gen.generate_multiple_clips_sync(
                prompts=lesson.video_prompts,
                aspect_ratio="9:16",
            )
            
            if video_clips:
                logger.info(f"Generated {len(video_clips)} video clips")
                composer = VideoComposer()
                final_video = composer.compose_video(
                    audio_path=audio_path,
                    video_paths=video_clips,
                    output_filename=f"lesson_{lesson.lesson_number}_{uuid4().hex[:8]}.mp4",
                )
                if final_video:
                    logger.info(f"Final video composed: {final_video}")
                    return final_video
            else:
                logger.warning("No video clips generated, returning audio-only")
            
            # Store audio path in lesson for reference
            lesson.audio_path = str(audio_path)
            
            return None
            
        except Exception as e:
            logger.error(f"Video production failed: {e}")
            return None
    
    def run_optimization_cycle(self) -> None:
        """Run the analytics and optimization cycle.
        
        This should be run periodically (e.g., weekly) to:
        1. Analyze recent performance
        2. Identify patterns
        3. Recommend strategy changes
        4. Optionally apply high-confidence recommendations
        """
        logger.info("Starting optimization cycle")
        
        # Analyze performance
        analysis = self.performance_analyst.analyze_performance(days=30)
        logger.info(f"Analyzed {analysis.videos_analyzed} videos")
        
        # Get optimization recommendations
        optimization = self.strategy_optimizer.optimize_strategy(analysis)
        
        logger.info(f"Strategy health: {optimization.overall_strategy_health}")
        logger.info(f"Recommendations: {len(optimization.recommendations)}")
        
        for rec in optimization.recommendations:
            logger.info(f"  [{rec.priority}] {rec.change_type}: {rec.recommended_value}")
        
        # Apply urgent changes automatically
        if optimization.urgent_changes:
            logger.warning(f"Applying urgent changes: {optimization.urgent_changes}")
            self.strategy_optimizer.apply_recommendations(
                optimization.recommendations,
                apply_priority_threshold=1  # Only apply priority 1 (urgent)
            )
        
        # Start A/B test if recommended
        if optimization.should_start_ab_test and optimization.ab_test_proposal:
            logger.info(f"Setting up A/B test: {optimization.ab_test_proposal}")
            # Parse and setup test
    
    def get_status(self) -> dict:
        """Get current system status.
        
        Returns:
            Dict with status information
        """
        active_plan = self.memory.get_active_topic_plan()
        strategy = self.memory.get_active_strategy()
        collection_stats = self.memory.get_collection_stats()
        
        return {
            "active_curriculum": {
                "topic": active_plan.main_topic if active_plan else None,
                "progress": f"{active_plan.current_index}/{active_plan.total_lessons}" if active_plan else None,
                "next_lesson": active_plan.current_subtopic if active_plan else None,
            } if active_plan else None,
            "strategy": {
                "script_style": strategy.current_script_style.value if strategy else None,
                "posting_times": strategy.posting_times if strategy else None,
                "ab_test_active": strategy.ab_test_active if strategy else False,
            } if strategy else None,
            "memory_stats": collection_stats,
        }
    
    def initialize_default_strategy(self) -> ContentStrategy:
        """Create and save a default content strategy.
        
        Returns:
            The created ContentStrategy
        """
        strategy = ContentStrategy(
            id=str(uuid4()),
            posting_times={
                "youtube": settings.post_time_youtube,
                "instagram": settings.post_time_instagram,
            },
        )
        
        self.memory.save_strategy(strategy)
        logger.info("Default strategy initialized")
        
        return strategy
