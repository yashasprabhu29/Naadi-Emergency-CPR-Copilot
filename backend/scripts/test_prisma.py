"""CLI smoke test for staged Gnani Prisma REST transcription."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Support both documented invocation styles:
#   python backend/scripts/test_prisma.py --audio ... (repository root)
#   cd backend && python scripts/test_prisma.py --audio ...
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.app.services.prisma_client import (
    AudioValidationError,
    PrismaAPIError,
    PrismaClient,
    PrismaClientError,
    PrismaConfigurationError,
    PrismaNetworkError,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Transcribe a staged audio recording with Gnani Prisma v3.0."
    )
    parser.add_argument("--audio", required=True, type=Path, help="Path to an audio file")
    parser.add_argument(
        "--language-code",
        default=None,
        help="Optional language hint; defaults to configured kn-IN,en-IN",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        default=None,
        choices=("verbatim", "transcribe", "codemix", "transliterate"),
        help="Optional Prisma output format; defaults to configured codemix",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        result = PrismaClient().transcribe(
            args.audio,
            language_code=args.language_code,
            format=args.output_format,
        )
    except PrismaConfigurationError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    except AudioValidationError as exc:
        print(f"Audio validation error: {exc}", file=sys.stderr)
        return 2
    except PrismaAPIError as exc:
        print(f"Prisma API error: {exc}", file=sys.stderr)
        return 1
    except PrismaNetworkError as exc:
        print(f"Network error: {exc}", file=sys.stderr)
        return 1
    except PrismaClientError as exc:
        print(f"Prisma client error: {exc}", file=sys.stderr)
        return 1

    print(f"Transcript: {result.transcript}")
    print(f"Detected language: {result.detected_language_code or 'not returned'}")
    print(f"Model: {result.model or 'not returned'}")
    print(f"Request ID: {result.request_id or 'not returned'}")
    if result.processing_time is not None:
        print(f"Processing time: {result.processing_time:.3f}s")
    if result.end_to_end_latency is not None:
        print(f"End-to-end latency: {result.end_to_end_latency:.3f}s")
    if result.truncated:
        print("Warning: Prisma marked this transcript as truncated.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
