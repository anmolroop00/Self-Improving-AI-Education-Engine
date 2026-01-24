import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config import settings
from google import genai

async def verify_genai():
    print(f"Checking API Key: {settings.google_api_key[:5]}...{settings.google_api_key[-5:] if settings.google_api_key else 'None'}")
    
    if not settings.google_api_key:
        print("❌ No Google API Key found in settings.")
        return

    try:
        if settings.google_cloud_project:
            print(f"Using Vertex AI with Project: {settings.google_cloud_project}, Location: {settings.google_cloud_location}")
            client = genai.Client(
                vertexai=True,
                project=settings.google_cloud_project,
                location=settings.google_cloud_location
            )
        else:
            print("Using API Key Authentication")
            client = genai.Client(api_key=settings.google_api_key)
        
        print("Attempting to generate content with Gemini 2.0 Flash...")
        response = await client.aio.models.generate_content(
            model="gemini-2.0-flash",
            contents="Say 'Hello, World!' if you can hear me."
        )
        print(f"✅ Success! Response: {response.text}")
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        print("\nTroubleshooting tips:")
        print("1. If using a Google Cloud API Key, ensure 'Generative Language API' is enabled.")
        print("2. If using Vertex AI specifically, code changes may be required to use `vertexai=True`.")

    print("\n--------------------------------")
    print("Checking Google Application Credentials...")
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or settings.google_application_credentials
    print(f"Path: {creds_path}")
    
    if not creds_path:
         print("❌ GOOGLE_APPLICATION_CREDENTIALS not set.")
    else:
        path_obj = Path(creds_path)
        if path_obj.exists():
             print("✅ Credentials file found.")
             try:
                 from google.oauth2 import service_account
                 creds = service_account.Credentials.from_service_account_file(creds_path)
                 print(f"✅ Credentials loaded successfully. Service Account: {creds.service_account_email}")
             except Exception as e:
                 print(f"❌ Failed to load credentials: {e}")
        else:
             print(f"❌ Credentials file NOT found at: {path_obj}")
             if " " in str(path_obj):
                 print("⚠️ Path contains spaces. Ensure it is quoted in .env if loading via dotenv.")

if __name__ == "__main__":
    asyncio.run(verify_genai())
