"""YouTube OAuth Setup Script.

Run this script once to authenticate with YouTube and generate credentials.
After running, your youtube_credentials.json will be created.
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]

def main():
    """Run OAuth flow and save credentials."""
    client_secrets = os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "client_secrets.json")
    credentials_file = os.getenv("YOUTUBE_CREDENTIALS_FILE", "youtube_credentials.json")
    
    print(f"Client secrets file: {client_secrets}")
    print(f"Credentials will be saved to: {credentials_file}")
    
    if not Path(client_secrets).exists():
        print(f"\n❌ ERROR: Client secrets file not found at: {client_secrets}")
        print("Please ensure your YouTube OAuth client secrets JSON is in place.")
        return
    
    print("\n🔐 Starting YouTube OAuth flow...")
    print("A browser window will open. Please sign in with your YouTube account.\n")
    
    flow = InstalledAppFlow.from_client_secrets_file(client_secrets, SCOPES)
    
    # This will open a browser for authentication
    credentials = flow.run_local_server(port=8080)
    
    # Save credentials
    with open(credentials_file, "w") as f:
        f.write(credentials.to_json())
    
    print(f"\n✅ SUCCESS! Credentials saved to: {credentials_file}")
    print("You can now run the full pipeline with YouTube uploads.")

if __name__ == "__main__":
    main()
