"""Seedance 2.5 text-to-video via the official Higgsfield SDK.

Credentials: HF_KEY (key-id:key-secret) in .env.local, loaded at runtime.
Usage: python main.py
"""
import sys

import httpx

import higgsfield_client
from higgsfield_app.client import has_credentials, iter_media_urls  # also loads .env.local

MODEL = 'bytedance/seedance-2.5/text-to-video'
ARGUMENTS = {
    'prompt': 'A cinematic scene at sunset',
    'duration': 5,
    'resolution': '720p',
    'aspect_ratio': '16:9',
}

FAILURE_MESSAGES = {
    'failed': 'Generation failed.',
    'nsfw': 'Generation was blocked by content moderation (NSFW).',
    'canceled': 'Generation was canceled.',
}


def video_url(result: dict) -> str | None:
    video = result.get('video')
    if isinstance(video, dict) and video.get('url'):
        return video['url']
    return next(iter_media_urls(result), None)


def main() -> int:
    if not has_credentials():
        print('HF_KEY is not set. Add HF_KEY=key-id:key-secret to .env.local.', file=sys.stderr)
        return 1

    try:
        result = higgsfield_client.subscribe(
            MODEL,
            arguments=ARGUMENTS,
            on_enqueue=lambda request_id: print(f'Request queued: {request_id}', file=sys.stderr),
            on_queue_update=lambda status: print(f'Status: {type(status).__name__}', file=sys.stderr),
        )
    except httpx.HTTPStatusError as exc:
        print(f'API error {exc.response.status_code}: {exc.response.text}', file=sys.stderr)
        return 1
    except httpx.HTTPError as exc:
        print(f'Could not reach the Higgsfield API: {exc}', file=sys.stderr)
        return 1

    # subscribe() returns the final request payload whatever the outcome,
    # so the status must be checked before treating it as a success.
    status = result.get('status')
    if status != 'completed':
        print(FAILURE_MESSAGES.get(status, f'Request ended with status {status!r}.'), file=sys.stderr)
        return 1

    url = video_url(result)
    if not url:
        print('Request completed but no video URL was returned.', file=sys.stderr)
        return 1

    print(url)
    return 0


if __name__ == '__main__':
    sys.exit(main())
