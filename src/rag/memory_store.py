"""ChromaDB-based Memory Store for RAG operations.

Provides persistent vector storage for curriculum plans, video performance,
content strategies, and other data needed for the self-improving system.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar
from uuid import uuid4

import chromadb
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

from ..config import settings
from .schemas import (
    ContentStrategy,
    HashtagPerformance,
    LessonContent,
    Platform,
    StrategyChange,
    TopicPlan,
    VideoPerformance,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class MemoryStore:
    """Central memory store using ChromaDB for vector storage.
    
    Manages multiple collections for different data types:
    - curriculum: Topic plans and lesson sequences
    - lessons: Generated lesson content
    - performance: Video analytics data
    - hashtags: Hashtag effectiveness tracking
    - strategies: Content strategy configurations
    - strategy_changes: History of strategy modifications
    
    Uses sentence-transformers for embedding generation.
    """
    
    # Collection names
    COLLECTION_CURRICULUM = "curriculum"
    COLLECTION_LESSONS = "lessons"
    COLLECTION_PERFORMANCE = "performance"
    COLLECTION_HASHTAGS = "hashtags"
    COLLECTION_STRATEGIES = "strategies"
    COLLECTION_STRATEGY_CHANGES = "strategy_changes"
    
    def __init__(self, persist_directory: Optional[Path] = None):
        """Initialize the memory store.
        
        Args:
            persist_directory: Where to store ChromaDB data. Uses config default if None.
        """
        self.persist_directory = persist_directory or settings.effective_chromadb_dir
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB with persistent storage (new API for v0.4+)
        self._client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=chromadb.Settings(anonymized_telemetry=False)
        )
        
        # Initialize embedding model (runs locally)
        logger.info("Loading embedding model...")
        self._embedder = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Embedding model loaded.")
        
        # Initialize collections
        self._collections: Dict[str, chromadb.Collection] = {}
        self._init_collections()
    
    def _init_collections(self) -> None:
        """Initialize all required collections."""
        collection_names = [
            self.COLLECTION_CURRICULUM,
            self.COLLECTION_LESSONS,
            self.COLLECTION_PERFORMANCE,
            self.COLLECTION_HASHTAGS,
            self.COLLECTION_STRATEGIES,
            self.COLLECTION_STRATEGY_CHANGES,
        ]
        
        for name in collection_names:
            self._collections[name] = self._client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.debug(f"Collection '{name}' ready with {self._collections[name].count()} items")
    
    def _embed(self, text: str) -> List[float]:
        """Generate embedding for text.
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        return self._embedder.encode(text).tolist()
    
    def _generate_id(self) -> str:
        """Generate a unique ID."""
        return str(uuid4())
    
    # ==================== Topic Plan Operations ====================
    
    def save_topic_plan(self, plan: TopicPlan) -> str:
        """Save a topic plan to the curriculum collection.
        
        Args:
            plan: TopicPlan to save
            
        Returns:
            The plan's ID
        """
        # Create searchable text from plan
        search_text = f"{plan.main_topic} {plan.description} {' '.join(plan.subtopics)}"
        
        self._collections[self.COLLECTION_CURRICULUM].upsert(
            ids=[plan.id],
            embeddings=[self._embed(search_text)],
            documents=[search_text],
            metadatas=[{
                "data": plan.model_dump_json(),
                "main_topic": plan.main_topic,
                "completed": plan.completed,
                "created_at": plan.created_at.isoformat()
            }]
        )
        
        logger.info(f"Saved topic plan: {plan.main_topic} ({plan.id})")
        return plan.id
    
    def get_topic_plan(self, plan_id: str) -> Optional[TopicPlan]:
        """Retrieve a topic plan by ID.
        
        Args:
            plan_id: The plan's unique ID
            
        Returns:
            TopicPlan if found, None otherwise
        """
        result = self._collections[self.COLLECTION_CURRICULUM].get(
            ids=[plan_id],
            include=["metadatas"]
        )
        
        if result["metadatas"]:
            data = json.loads(result["metadatas"][0]["data"])
            return TopicPlan(**data)
        return None
    
    def get_active_topic_plan(self) -> Optional[TopicPlan]:
        """Get the currently active (incomplete) topic plan.
        
        Returns:
            The first incomplete TopicPlan, or None if all are complete
        """
        result = self._collections[self.COLLECTION_CURRICULUM].get(
            where={"completed": False},
            include=["metadatas"]
        )
        
        if result["metadatas"]:
            # Sort by created_at and return the oldest incomplete plan
            plans = [
                TopicPlan(**json.loads(m["data"])) 
                for m in result["metadatas"]
            ]
            plans.sort(key=lambda p: p.created_at)
            return plans[0] if plans else None
        return None
    
    def search_topic_plans(self, query: str, limit: int = 5) -> List[TopicPlan]:
        """Search topic plans by semantic similarity.
        
        Args:
            query: Search query
            limit: Maximum results to return
            
        Returns:
            List of matching TopicPlans
        """
        result = self._collections[self.COLLECTION_CURRICULUM].query(
            query_embeddings=[self._embed(query)],
            n_results=limit,
            include=["metadatas"]
        )
        
        plans = []
        if result["metadatas"]:
            for metadata_list in result["metadatas"]:
                for metadata in metadata_list:
                    data = json.loads(metadata["data"])
                    plans.append(TopicPlan(**data))
        
        return plans
    
    def update_topic_progress(self, plan_id: str) -> Optional[TopicPlan]:
        """Advance the topic plan to the next lesson.
        
        Args:
            plan_id: The plan's ID
            
        Returns:
            Updated TopicPlan, or None if not found
        """
        plan = self.get_topic_plan(plan_id)
        if plan:
            plan.current_index += 1
            if plan.current_index >= plan.total_lessons:
                plan.completed = True
            self.save_topic_plan(plan)
            return plan
        return None
    
    # ==================== Lesson Content Operations ====================
    
    def save_lesson(self, lesson: LessonContent) -> str:
        """Save generated lesson content.
        
        Args:
            lesson: LessonContent to save
            
        Returns:
            The lesson's ID
        """
        search_text = f"{lesson.subtopic} {lesson.clean_script}"
        
        self._collections[self.COLLECTION_LESSONS].upsert(
            ids=[lesson.id],
            embeddings=[self._embed(search_text)],
            documents=[search_text],
            metadatas=[{
                "data": lesson.model_dump_json(),
                "topic_plan_id": lesson.topic_plan_id,
                "subtopic": lesson.subtopic,
                "lesson_number": lesson.lesson_number,
                "created_at": lesson.created_at.isoformat()
            }]
        )
        
        logger.info(f"Saved lesson {lesson.lesson_number}: {lesson.subtopic}")
        return lesson.id
    
    def get_lesson(self, lesson_id: str) -> Optional[LessonContent]:
        """Retrieve a lesson by ID."""
        result = self._collections[self.COLLECTION_LESSONS].get(
            ids=[lesson_id],
            include=["metadatas"]
        )
        
        if result["metadatas"]:
            data = json.loads(result["metadatas"][0]["data"])
            return LessonContent(**data)
        return None
    
    def get_lessons_for_topic(self, topic_plan_id: str) -> List[LessonContent]:
        """Get all lessons for a topic plan."""
        result = self._collections[self.COLLECTION_LESSONS].get(
            where={"topic_plan_id": topic_plan_id},
            include=["metadatas"]
        )
        
        lessons = []
        if result["metadatas"]:
            for metadata in result["metadatas"]:
                data = json.loads(metadata["data"])
                lessons.append(LessonContent(**data))
        
        return sorted(lessons, key=lambda l: l.lesson_number)
    
    # ==================== Performance Operations ====================
    
    def save_performance(self, perf: VideoPerformance) -> str:
        """Save video performance data.
        
        Args:
            perf: VideoPerformance to save
            
        Returns:
            The performance record's ID
        """
        # Create searchable text including hashtags
        search_text = f"{perf.platform.value} views:{perf.views} {' '.join(perf.hashtags_used)}"
        
        self._collections[self.COLLECTION_PERFORMANCE].upsert(
            ids=[perf.id],
            embeddings=[self._embed(search_text)],
            documents=[search_text],
            metadatas=[{
                "data": perf.model_dump_json(),
                "lesson_id": perf.lesson_id,
                "platform": perf.platform.value,
                "views": perf.views,
                "engagement_rate": perf.engagement_rate,
                "post_time": perf.post_time.isoformat()
            }]
        )
        
        logger.info(f"Saved performance for lesson {perf.lesson_id} on {perf.platform.value}")
        return perf.id
    
    def get_performance_history(
        self, 
        platform: Optional[Platform] = None,
        limit: int = 50
    ) -> List[VideoPerformance]:
        """Get performance history, optionally filtered by platform.
        
        Args:
            platform: Filter by platform (optional)
            limit: Maximum records to return
            
        Returns:
            List of VideoPerformance records, newest first
        """
        where_clause = {"platform": platform.value} if platform else None
        
        result = self._collections[self.COLLECTION_PERFORMANCE].get(
            where=where_clause,
            include=["metadatas"],
            limit=limit
        )
        
        performances = []
        if result["metadatas"]:
            for metadata in result["metadatas"]:
                data = json.loads(metadata["data"])
                performances.append(VideoPerformance(**data))
        
        return sorted(performances, key=lambda p: p.post_time, reverse=True)
    
    def get_avg_engagement_rate(self, platform: Platform, days: int = 30) -> float:
        """Calculate average engagement rate for recent videos.
        
        Args:
            platform: Platform to analyze
            days: Number of days to look back
            
        Returns:
            Average engagement rate
        """
        performances = self.get_performance_history(platform, limit=100)
        
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        recent = [p for p in performances if p.post_time.timestamp() > cutoff]
        
        if not recent:
            return 0.0
        
        return sum(p.engagement_rate for p in recent) / len(recent)
    
    # ==================== Hashtag Operations ====================
    
    def update_hashtag_performance(
        self, 
        hashtag: str, 
        platform: Platform,
        views: int,
        engagement: int
    ) -> HashtagPerformance:
        """Update or create hashtag performance record.
        
        Args:
            hashtag: The hashtag (without #)
            platform: Platform
            views: Views from the video
            engagement: Total engagement (likes + comments + shares)
            
        Returns:
            Updated HashtagPerformance
        """
        hashtag_id = f"{platform.value}_{hashtag.lower()}"
        
        # Try to get existing record
        result = self._collections[self.COLLECTION_HASHTAGS].get(
            ids=[hashtag_id],
            include=["metadatas"]
        )
        
        if result["metadatas"]:
            perf = HashtagPerformance(**json.loads(result["metadatas"][0]["data"]))
        else:
            perf = HashtagPerformance(hashtag=hashtag, platform=platform)
        
        perf.update_stats(views, engagement)
        
        self._collections[self.COLLECTION_HASHTAGS].upsert(
            ids=[hashtag_id],
            embeddings=[self._embed(hashtag)],
            documents=[hashtag],
            metadatas=[{
                "data": perf.model_dump_json(),
                "hashtag": hashtag,
                "platform": platform.value,
                "times_used": perf.times_used,
                "effectiveness_score": perf.effectiveness_score
            }]
        )
        
        return perf
    
    def get_top_hashtags(
        self, 
        platform: Platform, 
        limit: int = 10
    ) -> List[HashtagPerformance]:
        """Get top performing hashtags for a platform.
        
        Args:
            platform: Platform to get hashtags for
            limit: Number of hashtags to return
            
        Returns:
            List of HashtagPerformance, sorted by effectiveness
        """
        result = self._collections[self.COLLECTION_HASHTAGS].get(
            where={"platform": platform.value},
            include=["metadatas"]
        )
        
        hashtags = []
        if result["metadatas"]:
            for metadata in result["metadatas"]:
                data = json.loads(metadata["data"])
                hashtags.append(HashtagPerformance(**data))
        
        return sorted(hashtags, key=lambda h: h.effectiveness_score, reverse=True)[:limit]
    
    # ==================== Strategy Operations ====================
    
    def save_strategy(self, strategy: ContentStrategy) -> str:
        """Save a content strategy.
        
        Args:
            strategy: ContentStrategy to save
            
        Returns:
            Strategy ID
        """
        # Deactivate previous strategies
        existing = self._collections[self.COLLECTION_STRATEGIES].get(
            where={"active": True},
            include=["metadatas"]
        )
        
        if existing["ids"]:
            for old_id in existing["ids"]:
                old_result = self._collections[self.COLLECTION_STRATEGIES].get(
                    ids=[old_id],
                    include=["metadatas"]
                )
                if old_result["metadatas"]:
                    old_strategy = ContentStrategy(**json.loads(old_result["metadatas"][0]["data"]))
                    old_strategy.active = False
                    self._collections[self.COLLECTION_STRATEGIES].update(
                        ids=[old_id],
                        metadatas=[{
                            "data": old_strategy.model_dump_json(),
                            "active": False,
                            "created_at": old_strategy.created_at.isoformat()
                        }]
                    )
        
        # Save new strategy
        search_text = f"strategy {strategy.current_script_style.value} {' '.join(strategy.engagement_hooks)}"
        
        self._collections[self.COLLECTION_STRATEGIES].upsert(
            ids=[strategy.id],
            embeddings=[self._embed(search_text)],
            documents=[search_text],
            metadatas=[{
                "data": strategy.model_dump_json(),
                "active": strategy.active,
                "created_at": strategy.created_at.isoformat()
            }]
        )
        
        logger.info(f"Saved strategy: {strategy.id}")
        return strategy.id
    
    def get_active_strategy(self) -> Optional[ContentStrategy]:
        """Get the currently active content strategy.
        
        Returns:
            Active ContentStrategy, or None if none exists
        """
        result = self._collections[self.COLLECTION_STRATEGIES].get(
            where={"active": True},
            include=["metadatas"]
        )
        
        if result["metadatas"]:
            data = json.loads(result["metadatas"][0]["data"])
            return ContentStrategy(**data)
        return None
    
    def save_strategy_change(self, change: StrategyChange) -> str:
        """Record a strategy change for history tracking.
        
        Args:
            change: StrategyChange to record
            
        Returns:
            Change record ID
        """
        search_text = f"{change.change_type} {change.reason}"
        
        self._collections[self.COLLECTION_STRATEGY_CHANGES].add(
            ids=[change.id],
            embeddings=[self._embed(search_text)],
            documents=[search_text],
            metadatas=[{
                "data": change.model_dump_json(),
                "change_type": change.change_type,
                "timestamp": change.timestamp.isoformat()
            }]
        )
        
        logger.info(f"Recorded strategy change: {change.change_type}")
        return change.id
    
    # ==================== Utility Methods ====================
    
    def persist(self) -> None:
        """Force persist all data to disk.
        
        Note: PersistentClient auto-persists, so this is now a no-op.
        Kept for API compatibility.
        """
        # PersistentClient auto-persists; no explicit call needed
        logger.debug("Persist called (auto-persisted by PersistentClient)")
    
    def get_collection_stats(self) -> Dict[str, int]:
        """Get item counts for all collections.
        
        Returns:
            Dict mapping collection name to item count
        """
        return {
            name: collection.count() 
            for name, collection in self._collections.items()
        }
