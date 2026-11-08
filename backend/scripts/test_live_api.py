"""Live API validation script for Gnani Prisma STT and Timbre TTS.

This script tests actual Gnani API integration with your configured API key.
It validates STT and TTS functionality with real API calls (NOT mocked).

Requirements:
1. Create .env file in project root: Copy-Item .env.example .env
2. Edit .env and set: GNANI_API_KEY=<your-actual-key>
3. Optionally: Place a test audio file in audio/test_recordings/
4. Run: python backend/scripts/test_live_api.py

IMPORTANT:
- This consumes Gnani API credits
- Uses REAL API endpoints (not mocks)
- Never commit .env file
- Test audio should be fictional emergency scenarios only
"""

import sys
from pathlib import Path

# Add project root to path so we can import backend.app modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import os
import time
from backend.app.config import get_settings
from backend.app.services.prisma_client import PrismaClient, PrismaClientError
from backend.app.services.timbre_client import TimbreClient, TimbreClientError

def print_header(title):
    """Print formatted header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def check_api_key():
    """Verify API key is configured."""
    print_header("API KEY CONFIGURATION CHECK")
    
    settings = get_settings()
    
    if not settings.has_gnani_api_key:
        print("❌ GNANI_API_KEY is NOT configured")
        print("\nTo configure:")
        print("1. Copy .env.example to .env")
        print("2. Edit .env and set GNANI_API_KEY=<your-key>")
        print("3. Run this script again")
        return False
    
    print("✓ GNANI_API_KEY is configured")
    print(f"✓ Base URL: {settings.gnani_base_url}")
    print(f"✓ Model: {settings.gnani_model}")
    print(f"✓ Language: {settings.gnani_language_code}")
    print(f"✓ Format: {settings.gnani_format}")
    return True


def test_stt_with_file(audio_path: Path):
    """Test Prisma STT with actual audio file."""
    print_header(f"PRISMA STT TEST - {audio_path.name}")
    
    client = PrismaClient()
    
    try:
        print(f"📤 Sending audio to Gnani Prisma...")
        print(f"   File: {audio_path}")
        print(f"   Size: {audio_path.stat().st_size:,} bytes")
        
        start_time = time.time()
        result = client.transcribe(audio_path)
        elapsed = time.time() - start_time
        
        print(f"\n✓ SUCCESS - Transcription completed in {elapsed:.2f}s")
        print(f"\nTranscript: {result.transcript}")
        print(f"\nMetadata:")
        print(f"  Request ID: {result.request_id}")
        print(f"  Model: {result.model}")
        print(f"  Detected Language: {result.detected_language_code}")
        print(f"  Processing Time: {result.processing_time:.3f}s" if result.processing_time else "  Processing Time: N/A")
        print(f"  E2E Latency: {result.end_to_end_latency:.3f}s" if result.end_to_end_latency else "  E2E Latency: N/A")
        print(f"  Truncated: {result.truncated}")
        
        return True, result
        
    except PrismaClientError as exc:
        print(f"\n❌ FAILED - {exc.__class__.__name__}")
        print(f"   {exc}")
        return False, None


def test_tts_prompts():
    """Test Timbre TTS with predefined emergency prompts."""
    print_header("TIMBRE TTS TEST - Emergency Prompts")
    
    client = TimbreClient()
    
    # List available prompts
    prompts = client.list_emergency_prompts()
    print(f"\n✓ Available prompts: {len(prompts)}")
    for prompt_id, metadata in prompts.items():
        print(f"  - {prompt_id:30s} [{metadata['language']}] {metadata['description']}")
    
    # Test synthesizing a Kannada prompt
    test_prompts = [
        ("start_cpr_kannada", "audio/prompts/test_cpr_kannada.wav"),
        ("check_breathing_hindi", "audio/prompts/test_breathing_hindi.wav"),
        ("start_cpr_english", "audio/prompts/test_cpr_english.wav"),
    ]
    
    success_count = 0
    for prompt_id, output_path in test_prompts:
        print(f"\n📤 Synthesizing: {prompt_id}")
        
        try:
            start_time = time.time()
            result = client.synthesize_prompt(prompt_id)
            elapsed = time.time() - start_time
            
            # Save audio
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_bytes(result.audio_bytes)
            
            print(f"✓ SUCCESS - Generated in {elapsed:.2f}s")
            print(f"   Audio size: {len(result.audio_bytes):,} bytes")
            print(f"   Content type: {result.content_type}")
            if result.audio_duration_estimate:
                print(f"   Duration: ~{result.audio_duration_estimate:.2f}s")
            print(f"   Saved to: {output_file}")
            
            success_count += 1
            
        except TimbreClientError as exc:
            print(f"❌ FAILED - {exc.__class__.__name__}")
            print(f"   {exc}")
    
    print(f"\n✓ {success_count}/{len(test_prompts)} TTS tests passed")
    return success_count == len(test_prompts)


def find_test_audio():
    """Find test audio files in audio/test_recordings/."""
    recordings_dir = Path("audio/test_recordings")
    
    if not recordings_dir.exists():
        return []
    
    audio_files = []
    for ext in [".wav", ".mp3", ".ogg", ".flac", ".aac", ".m4a"]:
        audio_files.extend(recordings_dir.glob(f"*{ext}"))
    
    # Filter out .gitkeep
    return [f for f in audio_files if f.name != ".gitkeep"]


def main():
    """Run live API validation tests."""
    print("\n" + "#" * 70)
    print("#  NAADI - Live Gnani API Integration Test")
    print("#  Tests actual API calls (NOT mocked)")
    print("#" * 70)
    
    # Check API key
    if not check_api_key():
        return 1
    
    # Test STT
    test_files = find_test_audio()
    
    if test_files:
        print(f"\n✓ Found {len(test_files)} test audio file(s)")
        for audio_file in test_files[:3]:  # Test first 3 files max
            success, result = test_stt_with_file(audio_file)
            if not success:
                print("\n⚠ STT test failed, continuing...")
    else:
        print("\n⚠ No test audio found in audio/test_recordings/")
        print("  Place a .wav, .mp3, or other supported file there to test STT")
        print("  Continuing with TTS tests...")
    
    # Test TTS
    if test_tts_prompts():
        print_header("FINAL RESULT")
        print("✓ TTS integration validated successfully")
    else:
        print_header("FINAL RESULT")
        print("❌ Some TTS tests failed")
        return 1
    
    print("\n" + "#" * 70)
    print("#  Integration test complete!")
    print("#  Check audio/prompts/ for generated TTS samples")
    print("#" * 70)
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(130)
    except Exception as exc:
        print(f"\n\n❌ Unexpected error: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
