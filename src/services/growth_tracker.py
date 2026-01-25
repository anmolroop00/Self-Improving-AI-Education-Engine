"""Growth Tracker Service.

Tracks subscriber goals, progress, and projections for ARIA's
autonomous content strategy optimization.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum

from pydantic import BaseModel, Field

from ..config import settings

logger = logging.getLogger(__name__)


class GrowthStatus(str, Enum):
    """Overall growth status relative to target."""
    ON_TRACK = "on_track"           # Meeting or exceeding trajectory
    SLIGHTLY_BEHIND = "slightly_behind"  # 5-15% behind
    SIGNIFICANTLY_BEHIND = "significantly_behind"  # >15% behind
    AHEAD = "ahead"                 # Exceeding target trajectory


class GrowthSnapshot(BaseModel):
    """A point-in-time snapshot of growth metrics."""
    date: datetime
    subscribers: int
    views_total: int = 0
    videos_published: int = 0
    avg_engagement_rate: float = 0.0


class GrowthProjection(BaseModel):
    """Projected growth trajectory."""
    projected_final_subscribers: int
    days_to_target: Optional[int] = None
    required_daily_growth: float
    current_daily_growth: float
    on_track: bool
    confidence: float = Field(ge=0.0, le=1.0)


class WeeklyGrowthReport(BaseModel):
    """Weekly growth analysis report."""
    week_start: datetime
    week_end: datetime
    
    # Subscriber metrics
    subscribers_start: int
    subscribers_end: int
    subscribers_gained: int
    subscriber_growth_rate: float
    
    # Content metrics  
    videos_published: int
    total_views: int
    avg_views_per_video: float
    avg_engagement_rate: float
    
    # Best performers
    best_video_title: Optional[str] = None
    best_video_views: int = 0
    
    # Projections
    projection: GrowthProjection
    status: GrowthStatus
    
    # Strategic recommendations (filled by Strategic Brain)
    recommendations: List[str] = Field(default_factory=list)
    strategy_changes_made: List[str] = Field(default_factory=list)


class GrowthTracker:
    """Tracks and analyzes growth towards subscriber goal.
    
    Maintains historical data and calculates projections for
    ARIA's autonomous strategy decisions.
    """
    
    def __init__(self, data_file: Optional[Path] = None):
        """Initialize growth tracker.
        
        Args:
            data_file: Path to growth data JSON file. Defaults to data/growth_history.json
        """
        self.target_subscribers = settings.subscriber_target
        self.target_date = datetime.strptime(settings.target_deadline, "%Y-%m-%d")
        self.start_date = datetime.now()  # Will be updated from data
        
        # Data storage
        self.data_file = data_file or Path(settings.effective_output_dir) / "growth_history.json"
        self.snapshots: List[GrowthSnapshot] = []
        
        self._load_data()
    
    def _load_data(self) -> None:
        """Load historical growth data from file."""
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                
                self.start_date = datetime.fromisoformat(data.get("start_date", datetime.now().isoformat()))
                self.snapshots = [
                    GrowthSnapshot(**s) for s in data.get("snapshots", [])
                ]
                logger.info(f"Loaded {len(self.snapshots)} growth snapshots")
                
            except Exception as e:
                logger.warning(f"Could not load growth data: {e}")
    
    def _save_data(self) -> None:
        """Save growth data to file."""
        try:
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "start_date": self.start_date.isoformat(),
                "target_subscribers": self.target_subscribers,
                "target_date": self.target_date.isoformat(),
                "snapshots": [s.model_dump() for s in self.snapshots],
            }
            
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
                
            logger.info(f"Saved growth data to {self.data_file}")
            
        except Exception as e:
            logger.error(f"Failed to save growth data: {e}")
    
    def record_snapshot(
        self,
        subscribers: int,
        views_total: int = 0,
        videos_published: int = 0,
        avg_engagement_rate: float = 0.0,
    ) -> GrowthSnapshot:
        """Record a new growth snapshot.
        
        Args:
            subscribers: Current subscriber count
            views_total: Total views to date
            videos_published: Total videos published
            avg_engagement_rate: Average engagement rate
            
        Returns:
            The recorded snapshot
        """
        snapshot = GrowthSnapshot(
            date=datetime.now(),
            subscribers=subscribers,
            views_total=views_total,
            videos_published=videos_published,
            avg_engagement_rate=avg_engagement_rate,
        )
        
        self.snapshots.append(snapshot)
        self._save_data()
        
        logger.info(f"Recorded growth snapshot: {subscribers} subscribers")
        return snapshot
    
    def get_current_subscribers(self) -> int:
        """Get most recent subscriber count."""
        if not self.snapshots:
            return 0
        return self.snapshots[-1].subscribers
    
    def get_starting_subscribers(self) -> int:
        """Get subscriber count at start of tracking."""
        if not self.snapshots:
            return 0
        return self.snapshots[0].subscribers
    
    def calculate_projection(self) -> GrowthProjection:
        """Calculate growth projection to target date.
        
        Returns:
            GrowthProjection with trajectory analysis
        """
        current_subs = self.get_current_subscribers()
        start_subs = self.get_starting_subscribers()
        
        now = datetime.now()
        days_elapsed = max((now - self.start_date).days, 1)
        days_remaining = max((self.target_date - now).days, 1)
        total_days = (self.target_date - self.start_date).days
        
        # Calculate growth rates
        subs_gained = current_subs - start_subs
        current_daily_growth = subs_gained / days_elapsed if days_elapsed > 0 else 0
        
        subs_needed = self.target_subscribers - current_subs
        required_daily_growth = subs_needed / days_remaining if days_remaining > 0 else float('inf')
        
        # Project final subscriber count at current rate
        projected_final = int(current_subs + (current_daily_growth * days_remaining))
        
        # Calculate days to reach target at current rate
        days_to_target = None
        if current_daily_growth > 0:
            days_to_target = int(subs_needed / current_daily_growth)
        
        # Determine if on track
        on_track = projected_final >= self.target_subscribers
        
        # Confidence based on data points and consistency
        confidence = min(0.9, len(self.snapshots) * 0.1)  # More data = more confidence
        
        return GrowthProjection(
            projected_final_subscribers=projected_final,
            days_to_target=days_to_target,
            required_daily_growth=required_daily_growth,
            current_daily_growth=current_daily_growth,
            on_track=on_track,
            confidence=confidence,
        )
    
    def get_status(self) -> GrowthStatus:
        """Get current growth status relative to target trajectory.
        
        Returns:
            GrowthStatus enum value
        """
        projection = self.calculate_projection()
        
        if projection.on_track:
            if projection.current_daily_growth > projection.required_daily_growth * 1.2:
                return GrowthStatus.AHEAD
            return GrowthStatus.ON_TRACK
        
        # Calculate how far behind
        gap_percent = 1 - (projection.current_daily_growth / projection.required_daily_growth)
        
        if gap_percent > 0.15:
            return GrowthStatus.SIGNIFICANTLY_BEHIND
        return GrowthStatus.SLIGHTLY_BEHIND
    
    def get_weekly_summary(self) -> Dict[str, Any]:
        """Get summary of last 7 days of growth.
        
        Returns:
            Dictionary with weekly metrics
        """
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        
        # Filter snapshots from last week
        week_snapshots = [s for s in self.snapshots if s.date >= week_ago]
        
        if len(week_snapshots) < 2:
            return {
                "subscribers_gained": 0,
                "avg_daily_growth": 0,
                "data_points": len(week_snapshots),
                "message": "Insufficient data for weekly summary",
            }
        
        start = week_snapshots[0]
        end = week_snapshots[-1]
        
        days = max((end.date - start.date).days, 1)
        gained = end.subscribers - start.subscribers
        
        return {
            "period_start": start.date.isoformat(),
            "period_end": end.date.isoformat(),
            "subscribers_start": start.subscribers,
            "subscribers_end": end.subscribers,
            "subscribers_gained": gained,
            "avg_daily_growth": gained / days,
            "data_points": len(week_snapshots),
        }
    
    def generate_progress_report(self) -> str:
        """Generate a text progress report for emails/logs.
        
        Returns:
            Formatted progress report string
        """
        current = self.get_current_subscribers()
        target = self.target_subscribers
        projection = self.calculate_projection()
        status = self.get_status()
        weekly = self.get_weekly_summary()
        
        days_remaining = (self.target_date - datetime.now()).days
        progress_pct = (current / target) * 100 if target > 0 else 0
        
        # Progress bar
        filled = int(progress_pct / 5)
        bar = "█" * filled + "░" * (20 - filled)
        
        report = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 GROWTH PROGRESS REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 TARGET: {target:,} subscribers by {self.target_date.strftime('%b %d, %Y')}
📈 CURRENT: {current:,} subscribers ({progress_pct:.1f}%)

[{bar}] {progress_pct:.1f}%

⏱️ DAYS REMAINING: {days_remaining}
📊 STATUS: {status.value.replace('_', ' ').upper()}

THIS WEEK:
  • Subscribers gained: {weekly.get('subscribers_gained', 0):+d}
  • Daily average: {weekly.get('avg_daily_growth', 0):.1f}/day

PROJECTION:
  • At current rate: {projection.projected_final_subscribers:,} subscribers
  • Required rate: {projection.required_daily_growth:.1f}/day
  • Current rate: {projection.current_daily_growth:.1f}/day
  • On track: {'✅ YES' if projection.on_track else '❌ NO'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        return report


# Global tracker instance
_tracker: Optional[GrowthTracker] = None

def get_growth_tracker() -> GrowthTracker:
    """Get or create the global growth tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = GrowthTracker()
    return _tracker
