# ============================================================
# 🫧🦋 ʀuɴAk - Music: YouTube search + download
# ============================================================
#
# Only imported when MUSIC_ENABLED is True (see config.py / music.py),
# so yt-dlp / py-yt-search never need to be installed if you don't
# want the voice-chat music feature at all.
# ============================================================

import asyncio
import glob
import logging
import os

log = logging.getLogger(__name__)

os.makedirs("downloads", exist_ok=True)


async def get_info(query: str) -> dict | None:
    """Search YouTube (accepts a search term or a youtube link) and
    return the top result's info, or None if nothing was found."""
    from py_yt import VideosSearch

    search = VideosSearch(query, limit=1)
    result = (await search.next())["result"]
    if not result:
        return None

    video = result[0]
    duration = video.get("duration") or "Live"
    seconds = 0
    if duration and duration != "Live":
        parts = [int(p) for p in duration.split(":")]
        for part in parts:
            seconds = seconds * 60 + part

    return {
        "id": video["id"],
        "title": video["title"],
        "duration": duration,
        "duration_seconds": seconds,
        "thumbnail": video["thumbnails"][0]["url"].split("?")[0] if video.get("thumbnails") else "",
        "link": video["link"],
    }


async def download(video_id: str, video: bool = False) -> str | None:
    """Download audio (or video) for a video id, reusing a cached file
    if we already grabbed this id before. Returns the local file path."""
    import yt_dlp

    existing = glob.glob(f"downloads/{video_id}.*")
    if existing:
        return existing[0]

    url = f"https://www.youtube.com/watch?v={video_id}"
    fmt = "best[height<=?720]" if video else "bestaudio/best"
    ydl_opts = {
        "format": fmt,
        "outtmpl": f"downloads/{video_id}.%(ext)s",
        "quiet": True,
        "no_warnings": True,
        "geo_bypass": True,
        "nocheckcertificate": True,
    }

    def _run_download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None, _run_download)
    except Exception:
        log.warning("yt-dlp download failed for %s", video_id, exc_info=True)
        return None

    files = glob.glob(f"downloads/{video_id}.*")
    return files[0] if files else None
