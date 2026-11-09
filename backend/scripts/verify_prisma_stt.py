"""Comprehensive Prisma v3.0 STT verification script.

Run this script when a staged test recording is available to perform
live Gnani Prisma validation.

Requirements:
1. Staged audio file in audio/test_recordings/
2. GNANI_API_KEY configured in project root .env
3. Audio must be fictional emergency scenario (not real emergency call)
4. Duration ≤ 30 seconds
5. Supported format: WAV, MP3, FLAC, OGG, AAC, or M4A

Usage:
    cd backend
    python scripts/verify_prisma_stt.py --audio ../audio/test_recordings/test.wav
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import argparse
import time
from backend.app.services.prisma_client import PrismaClient, PrismaClientError

def main():
    parser = argparse.ArgumentParser(description="Verify Gnani Prisma v3.0 STT integration")
    parser.add_argument("--audio", required=True, help="Path to test audio file")
    args = parser.parse_args()
    
    audio_path = Path(args.audio)
    
    print("=" * 70)
    print("PRISMA v3.0 STT LIVE VERIFICATION")
    print("=" * 70)
    
    print(f"\nTest audio: {audio_path.name}")
    print(f"File size: {audio_path.stat().st_size:,} bytes")
    
    if not audio_path.exists():
        print(f"❌ ERROR: File not found: {audio_path}")
        return 1
    
    client = PrismaClient()
    
    try:
        print("\n📤 Sending to Gnani Prisma v3.0...")
        start = time.time()
        result = client.transcribe(audio_path)
        latency = time.time() - start
        
        print(f"\n✓ SUCCESS")
        print(f"\nLatency: {latency:.3f}s")
        print(f"\nTranscript:")
        print(f"  {result.transcript}")
        print(f"\nMetadata:")
        print(f"  Request ID: {result.request_id}")
        print(f"  Model: {result.model}")
        print(f"  Detected Language: {result.detected_language_code}")
        
        if result.processing_time:
            print(f"  Processing Time: {result.processing_time:.3f}s")
        if result.end_to_end_latency:
            print(f"  E2E Latency: {result.end_to_end_latency:.3f}s")
        
        print(f"  Truncated: {result.truncated}")
        
        print(f"\n--- Verification Summary ---")
        print(f"✓ Authentication: SUCCESS")
        print(f"✓ Request: SUCCESS")
        print(f"✓ Response parsing: SUCCESS")
        print(f"✓ Transcript received: {len(result.transcript)} characters")
        print(f"✓ Language detection: {result.detected_language_code or 'N/A'}")
        
        return 0
        
    except PrismaClientError as e:
        print(f"\n❌ FAILED: {e.__class__.__name__}")
        print(f"   {str(e)}")
        
        print(f"\n--- Verification Summary ---")
        if "401" in str(e) or "AUTHENTICATION" in str(e):
            print(f"❌ Authentication: FAILED")
            print(f"   Check API key is valid and has STT scope")
        elif "403" in str(e) or "PERMISSION" in str(e):
            print(f"❌ Permission: FAILED")
            print(f"   Enable STT scope in Gnani dashboard")
        elif "INVALID_AUDIO" in str(e) or "ValidationError" in str(e):
            print(f"❌ Audio validation: FAILED")
            print(f"   Check audio format and duration")
        else:
            print(f"❌ Request: FAILED")
        
        return 1

if __name__ == "__main__":
    sys.exit(main())
