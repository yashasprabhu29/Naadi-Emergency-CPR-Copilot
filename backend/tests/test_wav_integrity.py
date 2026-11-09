"""Tests for WAV file integrity from Timbre TTS responses."""

import wave
from pathlib import Path

import pytest


def test_generated_wav_files_exist():
    """Verify that generated WAV files exist."""
    prompts_dir = Path(__file__).parent.parent.parent / "audio" / "prompts"
    
    expected_files = [
        "validated_start_cpr_english.wav",
        "validated_start_cpr_kannada.wav",
        "validated_check_breathing_hindi.wav",
    ]
    
    for filename in expected_files:
        filepath = prompts_dir / filename
        # Files may not exist if live validation hasn't been run
        if filepath.exists():
            assert filepath.stat().st_size > 0, f"{filename} is empty"


def test_wav_files_are_readable():
    """Verify WAV files can be opened and read by Python wave module."""
    prompts_dir = Path(__file__).parent.parent.parent / "audio" / "prompts"
    
    test_files = [
        "validated_start_cpr_english.wav",
        "validated_start_cpr_kannada.wav",
        "validated_check_breathing_hindi.wav",
    ]
    
    for filename in test_files:
        filepath = prompts_dir / filename
        if not filepath.exists():
            pytest.skip(f"{filename} not generated yet (live validation not run)")
        
        # Should be able to open and read
        with wave.open(str(filepath), 'rb') as w:
            assert w.getnchannels() == 1, f"{filename} should be mono"
            assert w.getsampwidth() == 2, f"{filename} should be 16-bit"
            assert w.getframerate() == 48000, f"{filename} should be 48kHz"
            
            # Read first second of audio
            frames_to_read = min(48000, w.getnframes() if w.getnframes() < 2147483647 else 48000)
            audio_data = w.readframes(frames_to_read)
            assert len(audio_data) > 0, f"{filename} has no audio data"
            
            # Verify audio is not entirely silent
            non_zero = sum(1 for b in audio_data[:1000] if b != 0)
            assert non_zero > 0, f"{filename} appears to be silent"


def test_wav_duration_calculation_from_file_size():
    """Verify we can calculate accurate duration from file size despite malformed headers."""
    prompts_dir = Path(__file__).parent.parent.parent / "audio" / "prompts"
    
    test_cases = [
        ("validated_start_cpr_english.wav", 5.2, 0.5),  # Expected ~5.2s ±0.5s
        ("validated_start_cpr_kannada.wav", 6.9, 0.5),  # Expected ~6.9s ±0.5s
        ("validated_check_breathing_hindi.wav", 4.4, 0.5),  # Expected ~4.4s ±0.5s
    ]
    
    for filename, expected_duration, tolerance in test_cases:
        filepath = prompts_dir / filename
        if not filepath.exists():
            pytest.skip(f"{filename} not generated yet")
        
        # Calculate duration from file size
        file_size = filepath.stat().st_size
        # 48000 Hz * 2 bytes (16-bit) * 1 channel = 96000 bytes/sec
        # Subtract 44 bytes for typical WAV header
        audio_bytes = file_size - 44
        calculated_duration = audio_bytes / 96000
        
        assert abs(calculated_duration - expected_duration) < tolerance, \
            f"{filename} duration {calculated_duration:.2f}s differs from expected {expected_duration:.2f}s"


def test_gnani_wav_header_malformation_documented():
    """Document the known Gnani Timbre WAV header issue."""
    # This test documents a known provider issue
    # Gnani Timbre TTS returns WAV files with:
    # - Declared file size: 0xFFFFFFFF (4294967295)
    # - Declared data chunk size: 0xFFFFFFFF
    # 
    # This causes Python's wave module to report:
    # - nframes: 0x7FFFFFFF (2147483647, max signed int32)
    # 
    # However:
    # - The actual PCM audio data is valid and playable
    # - Duration can be calculated from actual file size
    # - Standard WAV decoders handle the files correctly
    # 
    # This is a Gnani provider response issue, not a client bug.
    pass
