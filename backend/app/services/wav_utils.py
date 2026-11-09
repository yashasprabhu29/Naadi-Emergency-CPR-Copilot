"""Helpers for WAV files returned by streaming encoders."""

from __future__ import annotations

import struct

_PLACEHOLDER_SIZES = {0xFFFFFFFF, 0x7FFFFFFF, 0}


def repair_wav_header(audio: bytes) -> bytes:
    """Return WAV bytes whose RIFF and data sizes match the real length.

    Gnani Timbre streams WAV audio and leaves placeholder sizes (0xFFFFFFFF)
    in the header. Some players then report a 12-hour file or refuse to seek.
    Anything that is not a RIFF/WAVE file, or already has correct sizes, is
    returned unchanged.
    """

    if len(audio) < 12 or audio[:4] != b"RIFF" or audio[8:12] != b"WAVE":
        return audio

    offset = 12
    while offset + 8 <= len(audio):
        chunk_id = audio[offset : offset + 4]
        (chunk_size,) = struct.unpack_from("<I", audio, offset + 4)
        body = offset + 8
        if chunk_id == b"data":
            actual_data = len(audio) - body
            actual_riff = len(audio) - 8
            (riff_size,) = struct.unpack_from("<I", audio, 4)
            if chunk_size == actual_data and riff_size == actual_riff:
                return audio
            if chunk_size not in _PLACEHOLDER_SIZES and chunk_size <= actual_data and riff_size == actual_riff:
                return audio
            fixed = bytearray(audio)
            struct.pack_into("<I", fixed, 4, actual_riff)
            struct.pack_into("<I", fixed, offset + 4, actual_data)
            return bytes(fixed)
        if chunk_size in _PLACEHOLDER_SIZES and chunk_id != b"fmt ":
            return audio
        offset = body + chunk_size + (chunk_size % 2)

    return audio
