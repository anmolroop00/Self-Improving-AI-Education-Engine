# Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         AI EDUCATION ENGINE                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌──────────────┐     ┌──────────────┐     ┌──────────────┐           │
│   │  Scheduler   │────▶│ Orchestrator │────▶│  YouTube     │           │
│   │ (LaunchAgent)│     │   Agent      │     │  Client      │           │
│   └──────────────┘     └──────┬───────┘     └──────────────┘           │
│                               │                                          │
│         ┌─────────────────────┼─────────────────────┐                   │
│         ▼                     ▼                     ▼                   │
│   ┌──────────┐         ┌──────────┐         ┌──────────┐               │
│   │  Script  │         │  Video   │         │ Metadata │               │
│   │  Writer  │         │ Prompter │         │Optimizer │               │
│   └────┬─────┘         └────┬─────┘         └──────────┘               │
│        │                    │                                            │
│        ▼                    ▼                                            │
│   ┌──────────┐         ┌──────────┐                                     │
│   │   TTS    │         │  Veo 3   │                                     │
│   │ Service  │         │Generator │                                     │
│   └────┬─────┘         └────┬─────┘                                     │
│        │                    │                                            │
│        └────────┬───────────┘                                            │
│                 ▼                                                        │
│           ┌──────────┐                                                   │
│           │ Composer │                                                   │
│           └────┬─────┘                                                   │
│                │                                                         │
│                ▼                                                         │
│   ┌────────────────────────────────────────────────────────┐            │
│   │                  RAG MEMORY (ChromaDB)                  │            │
│   │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │            │
│   │  │Curriculum│ │ Lessons  │ │Performanc│ │ Strategy │  │            │
│   │  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │            │
│   └────────────────────────────────────────────────────────┘            │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Content Generation Flow

```
Curriculum → Script → Audio + Video → Final Video → YouTube
     ↓
   RAG Query for context
```

### 2. Optimization Flow

```
YouTube Analytics → Performance Analyst → Strategy Optimizer → RAG Update
                                                    ↓
                                        Next video uses updated strategy
```

## Key Components

### Orchestrator (src/agents/orchestrator.py)

The central coordinator that manages the entire pipeline:

```python
class Orchestrator:
    def run_daily_pipeline(self, topic=None, dry_run=False):
        # 1. Get current lesson from RAG
        # 2. Generate script
        # 3. Create TTS audio
        # 4. Generate video clips
        # 5. Compose final video
        # 6. Generate metadata
        # 7. Upload to YouTube
        # 8. Update curriculum progress
```

### Memory Store (src/rag/memory_store.py)

ChromaDB-based vector store with semantic search:

```python
class MemoryStore:
    # Collections:
    # - curriculum: Topic plans
    # - lessons: Generated content
    # - performance: Video analytics
    # - strategies: Content strategies
    
    def get_active_topic_plan(self) -> TopicPlan
    def save_lesson(self, lesson: LessonContent) -> str
    def get_performance_history(self, platform, limit) -> List[VideoPerformance]
    def update_topic_progress(self, plan_id: str) -> None
    def get_active_strategy(self) -> ContentStrategy
    def save_strategy(self, strategy: ContentStrategy) -> str
```

### Configuration (src/config.py)

Environment-aware settings with feature flags:

```python
class Settings:
    env_mode: EnvironmentMode  # production/development
    
    @property
    def is_dev(self) -> bool
    
    @property
    def effective_chromadb_dir(self) -> Path
    
    @property
    def features(self) -> FeatureFlags
```

## Database Schema

### TopicPlan

```python
class TopicPlan:
    id: str
    main_topic: str
    subtopics: List[str]
    current_index: int
    total_lessons: int
```

### LessonContent

```python
class LessonContent:
    id: str
    subtopic: str
    script: str
    video_prompts: List[VideoPrompt]
    youtube_hashtags: List[str]
    final_video_path: Optional[str]
```

### VideoPerformance

```python
class VideoPerformance:
    id: str
    lesson_id: str
    platform: Platform
    platform_video_id: str
    views: int
    likes: int
    comments: int
    engagement_rate: float
```

### ContentStrategy

```python
class ContentStrategy:
    id: str
    posting_times: Dict[str, str]
    primary_hashtags: Dict[str, List[str]]
    current_script_style: ScriptStyle
    engagement_hooks: List[str]
```

## External Services

| Service | Purpose | Module |
|---------|---------|--------|
| Gemini 2.0 Flash | Script generation, analysis | agents/*.py |
| Vertex AI | Gemini/Veo authentication | config.py (vertexai=True) |
| Veo 3 | Video clip generation | production/video_generator.py |
| ElevenLabs | Text-to-speech | production/tts_service.py |
| YouTube API v3 | Upload, analytics | platforms/youtube_client.py |
| YouTube Analytics API | Watch time, demographics | platforms/youtube_client.py |
| Instagram Graph API | Reels, insights | platforms/instagram_client.py |
| ChromaDB | Vector storage | rag/memory_store.py |

## Environment Separation

```
PRODUCTION                    DEVELOPMENT
───────────────────────────   ───────────────────────────
data/chromadb/                data/chromadb_dev/
output/                       output_dev/
YouTube uploads: YES          YouTube uploads: NO (dry_run)
Curriculum: Real              Curriculum: Test
```
