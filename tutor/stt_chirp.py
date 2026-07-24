"""Dedicated ASR via Google Cloud Speech-to-Text V2 (Chirp).

Env:
  GOOGLE_CLOUD_PROJECT              required for Chirp
  GOOGLE_APPLICATION_CREDENTIALS    path to service-account JSON (or use ADC)
  STT_CHIRP_LOCATION                default "us" (use a region that supports chirp_3)
  STT_CHIRP_MODEL                   default "chirp_3"
  STT_LANGUAGE_CODES                default "es-US,en-US" (comma-separated)

Chirp is real ASR — much less likely to invent Spanish on silence than Gemini.
"""

from __future__ import annotations

import os
from typing import Any

from . import config

SAMPLE_RATE = 16000
DEFAULT_LOCATION = "us"
DEFAULT_MODEL = "chirp_3"
DEFAULT_LANGS = ("es-US", "en-US")


def chirp_project() -> str:
    return (
        os.environ.get("GOOGLE_CLOUD_PROJECT")
        or os.environ.get("GCLOUD_PROJECT")
        or os.environ.get("GCP_PROJECT")
        or ""
    ).strip()


def chirp_location() -> str:
    return (os.environ.get("STT_CHIRP_LOCATION") or DEFAULT_LOCATION).strip()


def chirp_model() -> str:
    return (os.environ.get("STT_CHIRP_MODEL") or DEFAULT_MODEL).strip()


def language_codes() -> list[str]:
    raw = (os.environ.get("STT_LANGUAGE_CODES") or "es-US,en-US").strip()
    return [x.strip() for x in raw.split(",") if x.strip()] or list(DEFAULT_LANGS)


def chirp_available() -> bool:
    """True if project is set and client library + credentials look usable."""
    config.load_env()
    if not chirp_project():
        return False
    try:
        from google.cloud.speech_v2 import SpeechClient  # noqa: F401
    except ImportError:
        return False
    # Credentials: ADC or GOOGLE_APPLICATION_CREDENTIALS
    creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or ""
    if creds and not os.path.isfile(creds):
        return False
    return True


def _client():
    from google.api_core.client_options import ClientOptions
    from google.cloud.speech_v2 import SpeechClient

    loc = chirp_location()
    # Regional endpoint required for many Chirp models
    endpoint = f"{loc}-speech.googleapis.com"
    return SpeechClient(client_options=ClientOptions(api_endpoint=endpoint))


def transcribe_pcm(
    pcm: bytes,
    *,
    sample_rate: int = SAMPLE_RATE,
) -> tuple[str, dict[str, Any]]:
    """Recognize raw s16le mono PCM. Returns (transcript, meta)."""
    config.load_env()
    project = chirp_project()
    if not project:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT not set (needed for Chirp STT)")
    if not pcm or len(pcm) < sample_rate * 2 * 0.2:
        return "", {"provider": "chirp", "skipped": "too_short", "bytes": len(pcm or b"")}

    from google.cloud.speech_v2.types import cloud_speech

    client = _client()
    location = chirp_location()
    model = chirp_model()
    langs = language_codes()
    recognizer = f"projects/{project}/locations/{location}/recognizers/_"

    recognition_config = cloud_speech.RecognitionConfig(
        explicit_decoding_config=cloud_speech.ExplicitDecodingConfig(
            encoding=cloud_speech.ExplicitDecodingConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=sample_rate,
            audio_channel_count=1,
        ),
        language_codes=langs,
        model=model,
        features=cloud_speech.RecognitionFeatures(
            enable_automatic_punctuation=True,
        ),
    )
    request = cloud_speech.RecognizeRequest(
        recognizer=recognizer,
        config=recognition_config,
        content=pcm,
    )
    response = client.recognize(request=request)
    parts: list[str] = []
    confidences: list[float] = []
    for result in response.results:
        if not result.alternatives:
            continue
        alt = result.alternatives[0]
        t = (alt.transcript or "").strip()
        if t:
            parts.append(t)
        if alt.confidence:
            confidences.append(float(alt.confidence))
    text = " ".join(parts).strip()
    meta: dict[str, Any] = {
        "provider": "chirp",
        "model": model,
        "location": location,
        "project": project,
        "languages": langs,
        "bytes": len(pcm),
        "chars": len(text),
    }
    if confidences:
        meta["confidence"] = round(sum(confidences) / len(confidences), 4)
    return text, meta


def chirp_status() -> dict[str, Any]:
    return {
        "available": chirp_available(),
        "project": chirp_project() or None,
        "location": chirp_location(),
        "model": chirp_model(),
        "languages": language_codes(),
        "credentials_env": bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")),
        "library": _library_ok(),
    }


def _library_ok() -> bool:
    try:
        import google.cloud.speech_v2  # noqa: F401

        return True
    except ImportError:
        return False
