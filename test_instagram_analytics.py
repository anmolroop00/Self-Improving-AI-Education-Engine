#!/usr/bin/env python3
"""Test Instagram Analytics fetching using the configured credentials."""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
import requests

load_dotenv()

# Configuration
ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
USER_ID = os.getenv("INSTAGRAM_USER_ID")
BASE_URL = "https://graph.facebook.com/v19.0"


def test_credentials():
    """Verify Instagram credentials are valid."""
    print("=" * 60)
    print("🔐 Testing Instagram Credentials")
    print("=" * 60)
    
    url = f"{BASE_URL}/{USER_ID}"
    params = {
        "fields": "id,username,media_count,followers_count,follows_count",
        "access_token": ACCESS_TOKEN
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    if "error" in data:
        print(f"❌ Error: {data['error']['message']}")
        return False
    
    print(f"✅ Account: @{data.get('username', 'N/A')}")
    print(f"   Instagram ID: {data.get('id')}")
    print(f"   Media Count: {data.get('media_count', 'N/A')}")
    print(f"   Followers: {data.get('followers_count', 'N/A')}")
    print(f"   Following: {data.get('follows_count', 'N/A')}")
    return True


def get_account_insights():
    """Fetch account-level insights."""
    print("\n" + "=" * 60)
    print("📊 Account Insights (Last 30 Days)")
    print("=" * 60)
    
    url = f"{BASE_URL}/{USER_ID}/insights"
    
    # Account-level metrics
    metrics = [
        "impressions",
        "reach", 
        "profile_views",
        "accounts_engaged",
        "total_interactions",
    ]
    
    params = {
        "metric": ",".join(metrics),
        "period": "day",
        "since": int((datetime.now() - timedelta(days=30)).timestamp()),
        "until": int(datetime.now().timestamp()),
        "access_token": ACCESS_TOKEN
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    if "error" in data:
        print(f"⚠️  Insights Error: {data['error'].get('message', 'Unknown')}")
        print("   (Note: Some metrics require a Business/Creator account)")
        return None
    
    insights = {}
    for metric in data.get("data", []):
        name = metric.get("name")
        values = metric.get("values", [])
        total = sum(v.get("value", 0) for v in values if isinstance(v.get("value"), (int, float)))
        insights[name] = total
        print(f"   {name}: {total:,}")
    
    return insights


def get_recent_media():
    """Fetch recent media with insights."""
    print("\n" + "=" * 60)
    print("📸 Recent Media & Performance")
    print("=" * 60)
    
    url = f"{BASE_URL}/{USER_ID}/media"
    params = {
        "fields": "id,caption,media_type,timestamp,like_count,comments_count,permalink",
        "limit": 10,
        "access_token": ACCESS_TOKEN
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    if "error" in data:
        print(f"❌ Error: {data['error']['message']}")
        return []
    
    media_items = data.get("data", [])
    
    if not media_items:
        print("   No media found on this account.")
        return []
    
    print(f"\n   Found {len(media_items)} recent posts:\n")
    
    for i, media in enumerate(media_items, 1):
        caption = media.get("caption", "No caption")[:50] + "..." if media.get("caption") else "No caption"
        media_type = media.get("media_type", "Unknown")
        likes = media.get("like_count", 0)
        comments = media.get("comments_count", 0)
        timestamp = media.get("timestamp", "")[:10]
        
        print(f"   {i}. [{media_type}] {timestamp}")
        print(f"      Caption: {caption}")
        print(f"      ❤️ {likes:,} likes | 💬 {comments:,} comments")
        
        # Get detailed insights for video/reel content
        if media_type in ["VIDEO", "REELS"]:
            get_media_insights(media["id"])
        print()
    
    return media_items


def get_media_insights(media_id: str):
    """Get detailed insights for a specific media item."""
    url = f"{BASE_URL}/{media_id}/insights"
    
    # Video/Reel specific metrics
    metrics = ["plays", "reach", "saved", "shares", "total_interactions"]
    
    params = {
        "metric": ",".join(metrics),
        "access_token": ACCESS_TOKEN
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    if "error" not in data:
        for metric in data.get("data", []):
            name = metric.get("name")
            value = metric.get("values", [{}])[0].get("value", 0)
            print(f"      📈 {name}: {value:,}")


def analyze_performance():
    """Analyze overall performance and provide insights."""
    print("\n" + "=" * 60)
    print("🧠 Performance Analysis")
    print("=" * 60)
    
    url = f"{BASE_URL}/{USER_ID}/media"
    params = {
        "fields": "id,media_type,like_count,comments_count,timestamp",
        "limit": 25,
        "access_token": ACCESS_TOKEN
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    if "error" in data or not data.get("data"):
        print("   Unable to analyze - no media found")
        return
    
    media_items = data["data"]
    
    # Calculate averages
    total_likes = sum(m.get("like_count", 0) for m in media_items)
    total_comments = sum(m.get("comments_count", 0) for m in media_items)
    count = len(media_items)
    
    avg_likes = total_likes / count if count > 0 else 0
    avg_comments = total_comments / count if count > 0 else 0
    engagement_rate = ((total_likes + total_comments) / count) if count > 0 else 0
    
    print(f"\n   📊 Based on last {count} posts:")
    print(f"   ├── Average Likes: {avg_likes:.1f}")
    print(f"   ├── Average Comments: {avg_comments:.1f}")
    print(f"   └── Avg Engagement per Post: {engagement_rate:.1f}")
    
    # Find best performing content
    if media_items:
        best = max(media_items, key=lambda x: x.get("like_count", 0) + x.get("comments_count", 0))
        print(f"\n   🏆 Top Performer:")
        print(f"      Media ID: {best['id']}")
        print(f"      Type: {best.get('media_type', 'Unknown')}")
        print(f"      Engagement: {best.get('like_count', 0) + best.get('comments_count', 0):,}")


def main():
    """Run all analytics tests."""
    print("\n" + "🔷" * 30)
    print("   INSTAGRAM ANALYTICS TEST")
    print("🔷" * 30 + "\n")
    
    if not ACCESS_TOKEN or not USER_ID:
        print("❌ Missing credentials!")
        print("   Set INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_USER_ID in .env")
        return
    
    print(f"📌 User ID: {USER_ID}")
    print(f"📌 Token: {ACCESS_TOKEN[:20]}...{ACCESS_TOKEN[-10:]}")
    
    # Run tests
    if not test_credentials():
        print("\n❌ Credential test failed. Check your token and user ID.")
        return
    
    get_account_insights()
    get_recent_media()
    analyze_performance()
    
    print("\n" + "=" * 60)
    print("✅ Analytics test complete!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
