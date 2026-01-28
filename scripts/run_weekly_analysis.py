#!/usr/bin/env python3
"""Weekly Strategic Analysis Script.

Runs every Sunday to analyze the week's performance and generate
strategic recommendations from ARIA.

This script:
1. Collects the week's performance data from RAG
2. Gets YouTube analytics for published videos
3. Updates growth tracker with current subscriber count
4. Passes data to Strategic Brain for analysis
5. Applies approved strategic changes
6. Sends detailed report email to owner
"""

import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import settings
from src.rag.memory_store import MemoryStore
from src.rag.schemas import TopicPlan, ScriptStyle
from src.agents.strategic_brain import get_strategic_brain
from src.agents.agent_persona import ARIA
from src.services.growth_tracker import get_growth_tracker
from src.services.notification_service import EmailNotificationService
from src.platforms.youtube_client import YouTubeClient

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"logs/weekly_{datetime.now().strftime('%Y-%m-%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def apply_strategic_changes(memory: MemoryStore, analysis) -> bool:
    """Apply strategic changes from analysis to RAG memory.
    
    Args:
        memory: Memory store
        analysis: WeeklyStrategicAnalysis from Strategic Brain
        
    Returns:
        True if changes were applied
    """
    changes_made = False
    
    # Handle topic pivot
    if analysis.topic_decision.should_pivot:
        logger.info(f"📝 Applying topic pivot: {analysis.topic_decision.recommended_topic}")
        # Create new topic plan for the recommended topic
        new_plan = TopicPlan(
            main_topic=analysis.topic_decision.recommended_topic,
            target_audience="5-year-old",  # Default or from audience_decision
            total_lessons=10,
            lesson_titles=[],  # Will be populated by curriculum planner
        )
        memory.save_topic_plan(new_plan)
        changes_made = True
        logger.info(f"   New topic plan created: {new_plan.id}")
    
    # Handle audience change
    if analysis.audience_decision.should_change:
        logger.info(f"👥 Audience change recommended: {analysis.audience_decision.recommended_audience}")
        # For now, log it - audience is typically part of topic plan
        changes_made = True
    
    # Handle content style update
    if analysis.content_style.recommended_style:
        logger.info(f"🎨 Updating content style: {analysis.content_style.recommended_style}")
        current_strategy = memory.get_active_strategy()
        if current_strategy:
            # Map recommended style to ScriptStyle enum
            style_map = {
                "story": ScriptStyle.STORY,
                "tutorial": ScriptStyle.TUTORIAL,
                "exploration": ScriptStyle.EXPLORATION,
            }
            recommended = analysis.content_style.recommended_style.lower()
            new_style = style_map.get(recommended, current_strategy.current_script_style)
            if new_style != current_strategy.current_script_style:
                current_strategy.current_script_style = new_style
                memory.save_strategy(current_strategy)
                changes_made = True
                logger.info(f"   Script style updated to: {new_style.value}")
    
    # Log strategic actions for tracking
    if analysis.strategic_actions:
        logger.info(f"📋 {len(analysis.strategic_actions)} strategic actions identified:")
        for action in analysis.strategic_actions[:3]:  # Log top 3
            logger.info(f"   P{action.priority}: {action.description}")
    
    return changes_made


def get_week_performance(memory: MemoryStore, youtube: YouTubeClient) -> dict:
    """Collect performance data for the past week.
    
    Args:
        memory: Memory store for RAG data
        youtube: YouTube client for analytics
        
    Returns:
        Dictionary with week's performance metrics
    """
    now = datetime.now()
    week_ago = now - timedelta(days=7)
    
    # Get lessons published this week from RAG
    # This retrieves lesson content stored during the week
    lessons_this_week = []
    
    # Get performance data for recent videos
    video_performances = []
    total_views = 0
    total_likes = 0
    total_comments = 0
    best_video = {"title": "N/A", "views": 0}
    worst_video = {"title": "N/A", "views": float('inf')}
    
    # Get published video IDs from run history
    run_history_file = Path("output/run_history.json")
    if run_history_file.exists():
        import json
        with open(run_history_file) as f:
            runs = json.load(f)
        
        # Filter to this week's runs
        for run in runs:
            run_date = datetime.fromisoformat(run.get("timestamp", "2000-01-01"))
            if run_date >= week_ago:
                video_id = run.get("video_id")
                title = run.get("title", "Unknown")
                
                if video_id:
                    perf = youtube.get_video_performance(video_id)
                    if perf:
                        video_performances.append(perf)
                        total_views += perf.views
                        total_likes += perf.likes
                        total_comments += perf.comments
                        
                        if perf.views > best_video["views"]:
                            best_video = {"title": title, "views": perf.views}
                        if perf.views < worst_video["views"]:
                            worst_video = {"title": title, "views": perf.views}
    
    # Handle case where no videos this week
    if worst_video["views"] == float('inf'):
        worst_video = {"title": "N/A", "views": 0}
    
    videos_count = len(video_performances)
    avg_engagement = 0.0
    if total_views > 0:
        avg_engagement = (total_likes + total_comments) / total_views
    
    return {
        "videos_published": videos_count,
        "total_views": total_views,
        "avg_engagement_rate": avg_engagement,
        "best_video_title": best_video["title"],
        "best_video_views": best_video["views"],
        "worst_video_title": worst_video["title"],
        "worst_video_views": worst_video["views"],
    }


def get_current_subscriber_count(youtube: YouTubeClient) -> int:
    """Get current subscriber count from YouTube.
    
    Uses the YouTube Data API channels.list endpoint.
    """
    try:
        channel_stats = youtube.get_channel_stats()
        count = channel_stats.get("subscribers", 0)
        logger.info(f"Current subscriber count: {count}")
        return count
    except Exception as e:
        logger.warning(f"Failed to get subscriber count: {e}")
        return 0


def send_weekly_report_email(
    notification_service: EmailNotificationService,
    analysis,
    growth_report: str,
    week_data: dict,
) -> bool:
    """Send the weekly strategic report email.
    
    Args:
        notification_service: Email service
        analysis: WeeklyStrategicAnalysis from Strategic Brain
        growth_report: Progress report from growth tracker
        week_data: Raw week performance data
        
    Returns:
        True if sent successfully
    """
    # Build HTML email
    subject = f"🤖 {ARIA.name} Weekly Strategy Report - {datetime.now().strftime('%b %d, %Y')}"
    
    # Determine status color
    status_colors = {
        "healthy": "#22c55e",  # Green
        "needs_attention": "#f59e0b",  # Amber
        "critical": "#ef4444",  # Red
    }
    status_color = status_colors.get(analysis.overall_health, "#6b7280")
    
    # Build insights list
    insights_html = "\n".join([f"<li>{insight}</li>" for insight in analysis.top_insights])
    
    # Build what worked/didn't work
    worked_html = "\n".join([f"<li style='color: #22c55e;'>✓ {item}</li>" for item in analysis.what_worked])
    didnt_work_html = "\n".join([f"<li style='color: #ef4444;'>✗ {item}</li>" for item in analysis.what_didnt_work])
    
    # Build actions list
    actions_html = "\n".join([
        f"<li><strong>P{action.priority}:</strong> {action.description} - <em>{action.expected_impact}</em></li>"
        for action in analysis.strategic_actions
    ])
    
    # Topic decision section
    topic_section = ""
    if analysis.topic_decision.should_pivot:
        topic_section = f"""
        <div style="background: #fef3c7; padding: 15px; border-radius: 8px; margin: 15px 0;">
            <h3 style="color: #92400e; margin: 0;">⚠️ Topic Pivot Recommended</h3>
            <p><strong>From:</strong> {analysis.topic_decision.current_topic}</p>
            <p><strong>To:</strong> {analysis.topic_decision.recommended_topic}</p>
            <p><strong>Reasoning:</strong> {analysis.topic_decision.reasoning}</p>
            <p><strong>Expected Impact:</strong> {analysis.topic_decision.expected_impact}</p>
        </div>
        """
    
    # Audience decision section
    audience_section = ""
    if analysis.audience_decision.should_change:
        audience_section = f"""
        <div style="background: #dbeafe; padding: 15px; border-radius: 8px; margin: 15px 0;">
            <h3 style="color: #1e40af; margin: 0;">👥 Audience Change Recommended</h3>
            <p><strong>From:</strong> {analysis.audience_decision.current_audience}</p>
            <p><strong>To:</strong> {analysis.audience_decision.recommended_audience}</p>
            <p><strong>Reasoning:</strong> {analysis.audience_decision.reasoning}</p>
        </div>
        """
    
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f3f4f6; padding: 20px; }}
            .container {{ max-width: 700px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; }}
            .header {{ background: linear-gradient(135deg, #6366f1, #8b5cf6); padding: 30px; text-align: center; }}
            .header h1 {{ color: white; margin: 0; font-size: 24px; }}
            .header p {{ color: rgba(255,255,255,0.8); margin: 10px 0 0 0; }}
            .content {{ padding: 30px; }}
            .status-badge {{ display: inline-block; padding: 5px 15px; border-radius: 20px; font-weight: bold; color: white; }}
            .metric-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin: 20px 0; }}
            .metric {{ background: #f9fafb; padding: 15px; border-radius: 8px; text-align: center; }}
            .metric-value {{ font-size: 28px; font-weight: bold; color: #1f2937; }}
            .metric-label {{ font-size: 12px; color: #6b7280; text-transform: uppercase; }}
            .section {{ margin: 25px 0; }}
            .section h2 {{ color: #1f2937; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px; }}
            ul {{ padding-left: 20px; }}
            li {{ margin: 8px 0; }}
            .confidence {{ background: #f0fdf4; padding: 15px; border-radius: 8px; margin-top: 20px; }}
            .message {{ background: #eff6ff; padding: 20px; border-radius: 8px; margin-top: 20px; border-left: 4px solid #3b82f6; }}
            .footer {{ background: #1f2937; color: white; padding: 20px; text-align: center; }}
            pre {{ background: #1f2937; color: #a5f3fc; padding: 15px; border-radius: 8px; overflow-x: auto; white-space: pre-wrap; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🤖 {ARIA.name} Weekly Strategy Report</h1>
                <p>{ARIA.full_name}</p>
            </div>
            
            <div class="content">
                <div style="text-align: center; margin-bottom: 20px;">
                    <span class="status-badge" style="background: {status_color};">
                        {analysis.overall_health.upper().replace('_', ' ')}
                    </span>
                </div>
                
                <p style="font-size: 16px; color: #374151;">{analysis.week_summary}</p>
                
                <div class="metric-grid">
                    <div class="metric">
                        <div class="metric-value">{week_data.get('videos_published', 0)}</div>
                        <div class="metric-label">Videos Published</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{week_data.get('total_views', 0):,}</div>
                        <div class="metric-label">Total Views</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{week_data.get('avg_engagement_rate', 0):.1%}</div>
                        <div class="metric-label">Engagement</div>
                    </div>
                </div>
                
                <div class="section">
                    <h2>📊 Growth Trajectory</h2>
                    <pre>{growth_report}</pre>
                </div>
                
                <div class="section">
                    <h2>💡 Key Insights</h2>
                    <ul>{insights_html}</ul>
                </div>
                
                <div class="section">
                    <h2>✅ What Worked</h2>
                    <ul>{worked_html}</ul>
                    
                    <h2 style="margin-top: 20px;">❌ What Didn't Work</h2>
                    <ul>{didnt_work_html}</ul>
                </div>
                
                {topic_section}
                {audience_section}
                
                <div class="section">
                    <h2>🎬 Content Style Recommendations</h2>
                    <p><strong>Style:</strong> {analysis.content_style.recommended_style}</p>
                    <p><strong>Tone:</strong> {analysis.content_style.recommended_tone}</p>
                    <p><strong>Reasoning:</strong> {analysis.content_style.reasoning}</p>
                </div>
                
                <div class="section">
                    <h2>🚀 Action Plan</h2>
                    <ol>{actions_html}</ol>
                </div>
                
                <div class="section">
                    <h2>🔬 Experiments to Run</h2>
                    <ul>
                        {"".join([f"<li>{exp}</li>" for exp in analysis.experiments_to_run])}
                    </ul>
                </div>
                
                <div class="section">
                    <h2>📅 Next Week Focus</h2>
                    <p style="font-size: 18px; color: #4f46e5; font-weight: bold;">
                        {analysis.next_week_focus}
                    </p>
                </div>
                
                <div class="confidence">
                    <strong>Confidence in hitting 1000 subscribers:</strong> 
                    <span style="font-size: 24px; font-weight: bold; color: #16a34a;">
                        {analysis.confidence_in_hitting_target:.0%}
                    </span>
                </div>
                
                <div class="message">
                    <h3 style="margin-top: 0;">💬 Message from {ARIA.name}</h3>
                    <p style="font-style: italic;">"{analysis.message_to_owner}"</p>
                </div>
            </div>
            
            <div class="footer">
                <p>{ARIA.name} - Your Autonomous Content Strategist</p>
                <p style="font-size: 12px; opacity: 0.7;">Generated on {datetime.now().strftime('%B %d, %Y at %H:%M')}</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        notification_service._send_email(subject, html_body)
        logger.info("Weekly report email sent successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to send weekly report email: {e}")
        return False


def main():
    """Run the weekly strategic analysis."""
    logger.info("=" * 60)
    logger.info(f"🤖 {ARIA.name} WEEKLY STRATEGIC ANALYSIS")
    logger.info(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    logger.info("=" * 60)
    
    # Check if ARIA autonomous mode is enabled
    if not settings.features.aria_autonomous:
        logger.warning("ARIA autonomous mode is not enabled. Set FEATURE_ARIA_AUTONOMOUS=true")
        return
    
    try:
        # Initialize services
        memory = MemoryStore()
        youtube = YouTubeClient()
        notification = EmailNotificationService()
        tracker = get_growth_tracker()
        brain = get_strategic_brain()
        
        # 1. Collect week's performance data
        logger.info("📊 Collecting week's performance data...")
        week_data = get_week_performance(memory, youtube)
        logger.info(f"Found {week_data['videos_published']} videos with {week_data['total_views']:,} total views")
        
        # 2. Update growth tracker with current subscriber count
        # Note: This is a placeholder - need actual YouTube API for subscribers
        current_subs = get_current_subscriber_count(youtube)
        if current_subs > 0:
            tracker.record_snapshot(
                subscribers=current_subs,
                views_total=week_data['total_views'],
                videos_published=week_data['videos_published'],
                avg_engagement_rate=week_data['avg_engagement_rate'],
            )
        
        # 3. Get current strategy info from RAG
        current_plan = memory.get_active_topic_plan()
        current_topic = current_plan.main_topic if current_plan else "Unknown"
        current_progress = f"{current_plan.current_index}/{current_plan.total_lessons}" if current_plan else "0/0"
        
        current_strategy = memory.get_active_strategy()
        current_audience = "5-year-old learners"  # Default
        
        # 4. Calculate subscribers gained (from growth tracker)
        weekly_summary = tracker.get_weekly_summary()
        subscribers_gained = weekly_summary.get('subscribers_gained', 0)
        
        # 5. Run Strategic Brain analysis
        logger.info(f"🧠 Running {ARIA.name} Strategic Brain analysis...")
        analysis = brain.analyze_week(
            videos_published=week_data['videos_published'],
            total_views=week_data['total_views'],
            subscribers_gained=subscribers_gained,
            avg_engagement_rate=week_data['avg_engagement_rate'],
            best_video_title=week_data['best_video_title'],
            best_video_views=week_data['best_video_views'],
            worst_video_title=week_data['worst_video_title'],
            worst_video_views=week_data['worst_video_views'],
            current_topic=current_topic,
            current_audience=current_audience,
            current_lesson_progress=current_progress,
        )
        
        # 6. Log key decisions
        logger.info(f"📋 Analysis complete:")
        logger.info(f"   Overall health: {analysis.overall_health}")
        logger.info(f"   Topic pivot: {'YES' if analysis.topic_decision.should_pivot else 'NO'}")
        logger.info(f"   Audience change: {'YES' if analysis.audience_decision.should_change else 'NO'}")
        logger.info(f"   Confidence: {analysis.confidence_in_hitting_target:.0%}")
        
        # 7. Apply strategic changes if any
        if apply_strategic_changes(memory, analysis):
            logger.info("✅ Strategic changes applied to memory")
        
        # 8. Send weekly report email
        growth_report = tracker.generate_progress_report()
        if settings.features.email_notifications:
            logger.info("📧 Sending weekly report email...")
            send_weekly_report_email(notification, analysis, growth_report, week_data)
        
        logger.info("=" * 60)
        logger.info("✅ Weekly analysis complete!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Weekly analysis failed: {e}", exc_info=True)
        
        # Send failure notification
        if settings.features.email_notifications:
            try:
                notification = EmailNotificationService()
                notification.send_failure_notification(
                    error_message=str(e),
                    stage="Weekly Strategic Analysis",
                )
            except:
                pass
        
        sys.exit(1)


if __name__ == "__main__":
    main()
