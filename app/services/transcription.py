"""Audio transcription service using OpenAI's Speech-to-Text API."""

import io
from typing import Optional

from openai import OpenAI

from app.config.settings import settings
from app.config.logger import app_logger


def get_openai_client() -> OpenAI:
    """Get OpenAI client instance."""
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    return OpenAI(api_key=settings.OPENAI_API_KEY)


def transcribe_audio(
    audio_data: bytes,
    filename: str = "audio.webm",
    model: str = "gpt-4o-mini-transcribe",
    language: Optional[str] = None,
    prompt: Optional[str] = None,
) -> str:
    """Transcribe audio data to text using OpenAI's transcription API.

    Args:
        audio_data: Raw audio bytes (supports mp3, mp4, mpeg, mpga, m4a, wav, webm)
        filename: Original filename with extension to help identify format
        model: Transcription model to use (gpt-4o-transcribe, gpt-4o-mini-transcribe, whisper-1)
        language: Optional language code (ISO 639-1) to improve accuracy
        prompt: Optional prompt to guide transcription (helps with proper nouns, acronyms)

    Returns:
        Transcribed text string

    Raises:
        RuntimeError: If transcription fails or OpenAI API is unavailable
    """
    client = get_openai_client()

    # Create a file-like object from the audio bytes
    audio_file = io.BytesIO(audio_data)
    audio_file.name = filename

    try:
        app_logger.info(f"Transcribing audio file: {filename}, size: {len(audio_data)} bytes")

        # Build transcription parameters
        params = {
            "file": audio_file,
            "model": model,
            "response_format": "text",
        }

        if language:
            params["language"] = language

        if prompt:
            params["prompt"] = prompt

        transcription = client.audio.transcriptions.create(**params)

        # For text response format, the result is the text directly
        if isinstance(transcription, str):
            text = transcription.strip()
        else:
            text = transcription.text.strip() if hasattr(transcription, 'text') else str(transcription).strip()

        app_logger.info(f"Transcription successful, length: {len(text)} chars")
        return text

    except Exception as e:
        app_logger.error(f"Transcription failed: {e}")
        raise RuntimeError(f"Audio transcription failed: {str(e)}")
