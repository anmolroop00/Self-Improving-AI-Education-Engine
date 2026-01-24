"""Curriculum Planner Agent.

Responsible for:
- Breaking down AI topics into 60-second lesson chunks
- Planning logical progression from basics to advanced
- Storing curriculum in RAG for continuity
"""

from datetime import datetime
from typing import List, Optional, Type
from uuid import uuid4

from pydantic import BaseModel, Field

from .base_agent import BaseAgent
from ..rag.memory_store import MemoryStore
from ..rag.schemas import TopicPlan


class CurriculumOutput(BaseModel):
    """Structured output for curriculum planning."""
    main_topic: str = Field(description="The main AI topic name")
    description: str = Field(description="Brief description of what will be covered")
    subtopics: List[str] = Field(
        description="Ordered list of lesson subtopics, each suitable for a 60-second explanation",
        min_length=5,
        max_length=30
    )
    difficulty_progression: str = Field(
        description="Brief explanation of how difficulty progresses through lessons"
    )


class CurriculumPlannerAgent(BaseAgent[CurriculumOutput]):
    """Agent that plans educational curriculums for AI topics.
    
    Takes a main topic (e.g., "Regression") and creates a structured
    series of 60-second lessons that explain the topic from basics
    to practical applications, suitable for a 5-year-old's understanding.
    """
    
    @property
    def agent_name(self) -> str:
        return "Curriculum Planner"
    
    @property
    def system_prompt(self) -> str:
        return """You are an expert curriculum designer for AI education content.
Your task is to break down complex AI/ML topics into a series of 60-second video lessons.

CRITICAL REQUIREMENTS:
1. Each subtopic must be explainable in 60 seconds (roughly 150-180 words spoken)
2. Explain concepts as if talking to a 5-year-old - use simple analogies
3. Start with the absolute basics - assume zero prior knowledge
4. Progress logically from simple to more complex concepts
5. Include practical examples and real-world applications
6. Make each lesson self-contained but building on previous ones

LESSON STRUCTURE GUIDELINES:
- Lessons 1-3: What is it? Basic definition using everyday analogies
- Lessons 4-6: How does it work? Simple mechanics with visual examples
- Lessons 7-9: Why do we need it? Real-world problems it solves
- Lessons 10+: Deeper concepts, variations, practical tips

EXAMPLE: Breaking down "Linear Regression"
Bad: "Linear regression minimizes the sum of squared residuals"
Good: "Linear regression is like drawing a line through a bunch of dots to find the pattern"

Always prioritize clarity and simplicity over technical accuracy.
Children (and beginners) need to feel the concept before understanding the math."""

    @property
    def output_schema(self) -> Type[CurriculumOutput]:
        return CurriculumOutput
    
    def plan_curriculum(self, topic: str, num_lessons: Optional[int] = None) -> TopicPlan:
        """Create a curriculum plan for a given topic.
        
        Args:
            topic: The main AI topic to cover (e.g., "Regression", "Neural Networks")
            num_lessons: Target number of lessons (optional, AI decides if not provided)
            
        Returns:
            TopicPlan stored in memory and ready for lesson generation
        """
        # Check for existing curriculum on this topic
        existing = self.memory.search_topic_plans(topic, limit=1)
        if existing and not existing[0].completed:
            return existing[0]
        
        # Build the prompt
        prompt = f"""Create a comprehensive curriculum for teaching: {topic}

The curriculum should cover the topic completely from absolute basics to practical applications.
Target audience: Complete beginners with zero technical background.
Each lesson = 60 seconds of spoken content."""

        if num_lessons:
            prompt += f"\n\nTarget number of lessons: {num_lessons}"
        else:
            prompt += "\n\nCreate as many lessons as needed to cover the topic thoroughly (minimum 10)."
        
        # Get context from memory about what's been taught before
        context = {}
        recent_plans = self.memory.search_topic_plans("completed curriculum", limit=3)
        if recent_plans:
            context["previously_taught_topics"] = [p.main_topic for p in recent_plans]
        
        # Generate curriculum
        result = self.generate_sync(prompt, context)
        
        # Create TopicPlan
        plan = TopicPlan(
            id=str(uuid4()),
            main_topic=result.main_topic,
            description=result.description,
            subtopics=result.subtopics,
            current_index=0,
            total_lessons=len(result.subtopics),
            created_at=datetime.now(),
            completed=False
        )
        
        # Save to memory
        self.memory.save_topic_plan(plan)
        
        return plan
    
    def get_next_lesson(self) -> Optional[tuple[TopicPlan, str]]:
        """Get the next lesson to teach from the active curriculum.
        
        Returns:
            Tuple of (TopicPlan, subtopic) or None if no active curriculum
        """
        plan = self.memory.get_active_topic_plan()
        if plan and plan.current_subtopic:
            return (plan, plan.current_subtopic)
        return None
    
    def mark_lesson_complete(self, plan_id: str) -> Optional[TopicPlan]:
        """Mark the current lesson as complete and advance to next.
        
        Args:
            plan_id: The topic plan ID
            
        Returns:
            Updated TopicPlan
        """
        return self.memory.update_topic_progress(plan_id)
