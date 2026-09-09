import httpx

from app.core.config import settings

DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"
ELEVENLABS_URL_TEMPLATE = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"


async def transcribe_audio(audio_bytes: bytes, content_type: str) -> str:
    if not settings.deepgram_api_key:
        raise RuntimeError("DEEPGRAM_API_KEY is not set. Add it to backend/.env to enable voice input.")

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            DEEPGRAM_URL,
            params={"model": "nova-2", "smart_format": "true"},
            headers={
                "Authorization": f"Token {settings.deepgram_api_key}",
                "Content-Type": content_type,
            },
            content=audio_bytes,
        )

    if response.status_code >= 400:
        raise RuntimeError(f"Deepgram error: {response.text[:300]}")

    data = response.json()
    try:
        return data["results"]["channels"][0]["alternatives"][0]["transcript"]
    except (KeyError, IndexError) as exc:
        raise RuntimeError("Deepgram returned an unexpected response") from exc


async def synthesize_speech(text: str) -> bytes:
    if not settings.elevenlabs_api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is not set. Add it to backend/.env to enable voice output.")

    url = ELEVENLABS_URL_TEMPLATE.format(voice_id=settings.elevenlabs_voice_id)
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            url,
            headers={
                "xi-api-key": settings.elevenlabs_api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
            json={
                "text": text,
                "model_id": "eleven_turbo_v2_5",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
            },
        )

    if response.status_code >= 400:
        raise RuntimeError(f"ElevenLabs error: {response.text[:300]}")
    return response.content
