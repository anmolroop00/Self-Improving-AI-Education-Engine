"""Configuration management for the AI Education Engine.

Uses pydantic-settings for type-safe environment variable loading.
Supports dev/prod environment separation for safe feature testing.
"""

from enum import Enum
from pathlib import Path
from typing import Literal, Dict, Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load environment variables explicitly for libraries that rely on os.environ (like google-auth)
load_dotenv()


class EnvironmentMode(str, Enum):
    """Environment modes for dev/prod separation."""
    PRODUCTION = "production"
    DEVELOPMENT = "development"


class TTSProvider(str, Enum):
    """Available Text-to-Speech providers."""
    GOOGLE = "google"
    ELEVENLABS = "elevenlabs"


class ExplanationLevel(str, Enum):
    """Target audience comprehension level."""
    FIVE_YEAR_OLD = "5_year_old"
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"


class FeatureFlags(BaseSettings):
    """Feature flags for controlled rollout of new features."""
    
    model_config = SettingsConfigDict(
        env_prefix="FEATURE_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Feature toggles - set FEATURE_THUMBNAILS=true in .env to enable
    thumbnails: bool = Field(default=False, description="Enable AI thumbnail generation")
    captions: bool = Field(default=False, description="Enable auto-generated captions")
    multi_platform: bool = Field(default=False, description="Enable Instagram/TikTok posting")
    ab_testing: bool = Field(default=False, description="Enable A/B testing for titles")
    email_notifications: bool = Field(default=False, description="Enable email notifications")


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Environment Mode
    env_mode: EnvironmentMode = Field(
        default=EnvironmentMode.PRODUCTION, 
        description="Environment mode: development or production"
    )
    
    # Google Cloud Configuration
    google_cloud_project: str = Field(default="", description="GCP Project ID")
    google_cloud_location: str = Field(default="us-central1", description="GCP Region")
    google_application_credentials: str = Field(default="", description="Path to service account JSON")
    google_api_key: str = Field(default="", description="Google API Key for Gemini/Veo (Optional if using Vertex AI)")
    
    # TTS Configuration
    tts_provider: TTSProvider = Field(default=TTSProvider.GOOGLE, description="TTS provider to use")
    elevenlabs_api_key: str = Field(default="", description="Eleven Labs API Key")
    elevenlabs_voice_id: str = Field(default="", description="Eleven Labs Voice ID")
    
    # YouTube Configuration
    youtube_client_secrets_file: str = Field(default="client_secrets.json")
    youtube_credentials_file: str = Field(default="youtube_credentials.json")
    
    # Instagram Configuration
    instagram_access_token: str = Field(default="")
    instagram_user_id: str = Field(default="")
    video_host_url: str = Field(default="", description="Public URL for video hosting")
    
    # Email Notification Settings (SMTP)
    smtp_host: str = Field(default="smtp.gmail.com", description="SMTP server host")
    smtp_port: int = Field(default=587, description="SMTP server port")
    smtp_user: str = Field(default="", description="SMTP username (email)")
    smtp_password: str = Field(default="", description="SMTP password or app password")
    notification_from_email: str = Field(default="", description="From email address")
    notification_to_email: str = Field(default="", description="Notification recipient email")
    
    # ChromaDB Configuration (base path - will be modified based on env_mode)
    chromadb_persist_directory: Path = Field(default=Path("./data/chromadb"))
    
    # Video Settings
    video_output_dir: Path = Field(default=Path("./output"))
    video_target_duration: int = Field(default=60, description="Target video duration in seconds")
    video_aspect_ratio: str = Field(default="9:16", description="Video aspect ratio")
    
    # Content Settings
    default_topic: str = Field(default="machine_learning")
    script_target_words: int = Field(default=160, description="Target word count for 60s")
    explanation_level: ExplanationLevel = Field(default=ExplanationLevel.FIVE_YEAR_OLD)
    
    # Scheduling
    post_time_youtube: str = Field(default="10:00")
    post_time_instagram: str = Field(default="18:00")
    timezone: str = Field(default="Asia/Kolkata")
    
    # Logging
    log_level: str = Field(default="INFO")
    
    # Feature flags instance
    _features: FeatureFlags = None
    
    @property
    def is_dev(self) -> bool:
        """Check if running in development mode."""
        return self.env_mode == EnvironmentMode.DEVELOPMENT
    
    @property
    def is_prod(self) -> bool:
        """Check if running in production mode."""
        return self.env_mode == EnvironmentMode.PRODUCTION
    
    @property
    def features(self) -> FeatureFlags:
        """Get feature flags instance."""
        if self._features is None:
            self._features = FeatureFlags()
        return self._features
    
    @property
    def effective_chromadb_dir(self) -> Path:
        """Get ChromaDB directory based on environment mode."""
        if self.is_dev:
            return Path("./data/chromadb_dev")
        return self.chromadb_persist_directory
    
    @property
    def effective_output_dir(self) -> Path:
        """Get output directory based on environment mode."""
        if self.is_dev:
            return Path("./output_dev")
        return self.video_output_dir
    
    @property
    def default_dry_run(self) -> bool:
        """Default dry_run setting based on environment."""
        return self.is_dev  # Always dry_run in dev mode by default
    
    @property
    def audio_output_dir(self) -> Path:
        """Directory for generated audio files."""
        return self.effective_output_dir / "audio"
    
    @property
    def video_clips_dir(self) -> Path:
        """Directory for generated video clips."""
        return self.effective_output_dir / "video"
    
    @property
    def final_output_dir(self) -> Path:
        """Directory for final composed videos."""
        return self.effective_output_dir / "final"
    
    def ensure_directories(self) -> None:
        """Create all required output directories."""
        for dir_path in [
            self.effective_chromadb_dir,
            self.audio_output_dir,
            self.video_clips_dir,
            self.final_output_dir,
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def get_env_summary(self) -> Dict[str, Any]:
        """Get a summary of current environment settings."""
        return {
            "mode": self.env_mode.value,
            "chromadb_dir": str(self.effective_chromadb_dir),
            "output_dir": str(self.effective_output_dir),
            "dry_run_default": self.default_dry_run,
            "features": {
                "thumbnails": self.features.thumbnails,
                "captions": self.features.captions,
                "multi_platform": self.features.multi_platform,
                "ab_testing": self.features.ab_testing,
                "email_notifications": self.features.email_notifications,
            }
        }


# Global settings instance
settings = Settings()

