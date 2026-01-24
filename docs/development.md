# Development Guide

## Setting Up Development Environment

### 1. Switch to Dev Mode

```bash
# In .env, set:
ENV_MODE=development
```

Or use the dev runner which auto-sets dev mode:

```bash
python3 scripts/run_dev.py
```

### 2. Verify Environment

```bash
python3 scripts/run_dev.py --env-only
```

Expected output:
```
   Environment: DEVELOPMENT
   ChromaDB: data/chromadb_dev
   Output: output_dev
   Dry Run Default: True
```

## Adding New Features

### Step 1: Add Feature Flag

In `.env`:
```bash
FEATURE_MY_NEW_FEATURE=false
```

In `src/config.py`, add to `FeatureFlags`:
```python
class FeatureFlags(BaseSettings):
    my_new_feature: bool = Field(default=False)
```

### Step 2: Check Flag in Code

```python
from src.config import settings

if settings.features.my_new_feature:
    # New feature code here
    pass
```

### Step 3: Test in Dev Mode

```bash
# Enable feature for testing
python3 scripts/run_dev.py --feature my_new_feature
```

### Step 4: Enable in Production

When ready, update `.env`:
```bash
FEATURE_MY_NEW_FEATURE=true
```

## Code Style

### Agent Pattern

All AI agents follow this pattern:

```python
from .base_agent import BaseAgent

class MyAgent(BaseAgent[OutputSchema]):
    @property
    def agent_name(self) -> str:
        return "My Agent"
    
    @property
    def system_prompt(self) -> str:
        return """Your system prompt..."""
    
    @property
    def output_schema(self) -> Type[OutputSchema]:
        return OutputSchema
    
    def my_method(self, input_data) -> OutputSchema:
        prompt = f"Process this: {input_data}"
        return self.generate_sync(prompt)
```

### Schema Pattern

All data models use Pydantic:

```python
from pydantic import BaseModel, Field

class MySchema(BaseModel):
    id: str = Field(description="Unique identifier")
    name: str = Field(description="Display name")
    created_at: datetime = Field(default_factory=datetime.now)
```

## Testing Changes

### Quick Test (No Video Generation)

```bash
# Just check environment
python3 scripts/run_dev.py --env-only
```

### Full Test (With Video, No Upload)

```bash
# Uses dev database, generates real video
python3 scripts/run_dev.py --no-dry-run
```

### Production Test

```bash
# Force run in production mode
python3 scripts/run_daily.py --force
```

## Common Development Tasks

### View RAG Contents

```python
from src.rag.memory_store import MemoryStore
memory = MemoryStore()
print(memory.get_collection_stats())
```

### Reset Dev Curriculum

```python
# The dev runner creates a fresh test curriculum automatically
python3 scripts/run_dev.py
```

### Debug Agent Output

```python
import logging
logging.basicConfig(level=logging.DEBUG)

from src.agents.script_writer import ScriptWriterAgent
from src.rag.memory_store import MemoryStore

memory = MemoryStore()
writer = ScriptWriterAgent(memory=memory)
result = writer.write_script("Test topic")
print(result.model_dump_json(indent=2))
```

## File Locations

| What | Production | Development |
|------|------------|-------------|
| RAG Database | `data/chromadb/` | `data/chromadb_dev/` |
| Audio Files | `output/audio/` | `output_dev/audio/` |
| Video Clips | `output/video/` | `output_dev/video/` |
| Final Videos | `output/final/` | `output_dev/final/` |
| Logs | `logs/` | `logs/` (shared) |

## Troubleshooting

### Import Errors

```bash
# Ensure PYTHONPATH includes project root
export PYTHONPATH="/path/to/project:$PYTHONPATH"
```

### ChromaDB Errors

```bash
# Delete dev database and start fresh
rm -rf data/chromadb_dev
python3 scripts/run_dev.py
```

### Environment Not Switching

Make sure to import config AFTER setting ENV_MODE:

```python
import os
os.environ["ENV_MODE"] = "development"  # BEFORE import

from src.config import settings  # AFTER setting
```
