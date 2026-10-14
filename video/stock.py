"""
Free stock-image provider adapter.
Priority: Pixabay (when PIXABAY_API_KEY is configured), then Openverse.
Only download assets from providers; normalize images to JPEG for the renderer and
record Openverse attribution/license metadata for creators.
"""
import json
import os
import random
from pathlib import Path

import requests
from PIL import Image
from io import BytesIO

import config

PIXABAY_SEARCH = "https://pixabay.com/api/"
OPENVERSE_SEARCH = "https://api.openverse.org/v1/images/"
FALLBACK_QUERIES = [
    "space universe stars galaxy",
    "science technology futuristic",
    "earth atmosphere clouds aerial",
    "abstract light particles",
    "dramatic landscape nature",
    "neon city night lights",
]
OPENVERSE_LICENSES = "cc0,by,by-sa,pdm"


def _pixabay_results(query, orientation, per_page):
    key = getattr(config, "PIXABAY_API_KEY", "")
    if not key or key.startswith("YOUR_"):
        return []
    params = {
        "key": key,
        "q": query,
        "image_type": "photo",
        "safesearch": "true",
        "orientation": "vertical" if orientation == "portrait" else "horizontal",
        "per_page": per_page,
        "order": "popular",
    }
    response = requests.get(PIXABAY_SEARCH, params=params, timeout=15)
    if response.status_code in (400, 401, 403):
        print("   ⚠ Pixabay key rejected or request not allowed; trying Openverse.")
        return []
    response.raise_for_status()
    hits = response.json().get("hits", [])
    hits.sort(key=lambda item: item.get("imageWidth", 0) * item.get("imageHeight", 0), reverse=True)
    return [{
        "provider": "Pixabay",
        "url": item.get("largeImageURL") or item.get("webformatURL"),
        "title": item.get("tags", query),
        "license": "Pixabay Content License",
        "attribution": item.get("user", "Pixabay contributor"),
        "source_url": item.get("pageURL", ""),
    } for item in hits if item.get("largeImageURL") or item.get("webformatURL")]


def _openverse_results(query, orientation, per_page):
    params = {
        "q": query,
        "page_size": per_page,
        "license": OPENVERSE_LICENSES,
        "mature": "false",
    }
    response = requests.get(
        OPENVERSE_SEARCH,
        params=params,
        headers={"User-Agent": "AI-Vidro-Automation-Pipeline/1.0 (open-source video creator)"},
        timeout=20,
    )
    response.raise_for_status()
    results = response.json().get("results", [])
    random.shuffle(results)
    return [{
        "provider": "Openverse",
        "url": item.get("url"),
        "title": item.get("title") or query,
        "license": item.get("license", "unknown"),
        "license_version": item.get("license_version", ""),
        "attribution": item.get("attribution") or item.get("creator") or "Unknown creator",
        "source_url": item.get("foreign_landing_url") or item.get("detail_url") or "",
    } for item in results if item.get("url")]


def _search(query, orientation, count):
    per_page = min(max(count * 3, 12), 40)
    providers = []
    try:
        providers.extend(_pixabay_results(query, orientation, per_page))
    except Exception as exc:
        print(f"   ⚠ Pixabay search failed: {exc}")
    if len(providers) < count:
        try:
            providers.extend(_openverse_results(query, orientation, per_page))
        except Exception as exc:
            print(f"   ⚠ Openverse search failed: {exc}")
    random.shuffle(providers)
    return providers


def _download_asset(asset, path):
    response = requests.get(asset["url"], timeout=30, stream=True)
    response.raise_for_status()
    data = b"".join(response.iter_content(8192))
    if not data:
        raise ValueError("Provider returned an empty image")
    # Save as real JPEG bytes so downstream MoviePy/Pillow processing is predictable.
    with Image.open(BytesIO(data)) as source:
        source.convert("RGB").save(path, format="JPEG", quality=92, optimize=True)


def _fetch_images(query, section_index, images_dir, count=1, orientation="landscape",
                  img_num_start=0, topic_hint=""):
    search_query = query
    if topic_hint and topic_hint.lower() not in query.lower():
        search_query = f"{topic_hint} {query}"

    saved = []
    for attempt_query in [search_query, query] + FALLBACK_QUERIES:
        candidates = _search(attempt_query, orientation, max(count, 1))
        if not candidates:
            continue
        random.shuffle(candidates)
        for asset in candidates:
            if len(saved) >= count:
                break
            fname = f"section_{section_index:02d}_img{img_num_start + len(saved) + 1:02d}.jpg"
            path = os.path.join(images_dir, fname)
            try:
                _download_asset(asset, path)
                saved.append(path)
                if asset["provider"] == "Openverse":
                    _record_attribution(images_dir, fname, asset)
            except Exception as exc:
                print(f"   ⚠ Image download failed from {asset.get('provider', 'provider')}: {exc}")
        if saved:
            break
    return saved


def _record_attribution(images_dir, filename, asset):
    manifest_path = Path(images_dir) / "attribution.json"
    try:
        records = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else []
        records.append({
            "file": filename,
            "provider": asset.get("provider"),
            "title": asset.get("title"),
            "creator_attribution": asset.get("attribution"),
            "license": asset.get("license"),
            "license_version": asset.get("license_version", ""),
            "source_url": asset.get("source_url", ""),
        })
        manifest_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        print(f"   ⚠ Could not write image attribution manifest: {exc}")


def download_images(script: dict, output_dir: str) -> dict:
    """Download stock images for every script section; keep the existing image_map contract."""
    images_dir = os.path.join(output_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    is_shorts = script.get("video_type") == "shorts"
    orientation = "portrait" if is_shorts else "landscape"
    raw_title = script.get("title", "")
    topic_hint = " ".join(raw_title.split()[:4]) if raw_title else ""
    image_map = {}

    for section in script.get("sections", []):
        sid = section["id"]
        queries = [section.get("image_query", "science universe space")]
        for extra_key in ("image_query_2", "image_query_3", "image_query_4"):
            query = section.get(extra_key, "").strip()
            if query:
                queries.append(query)

        # Preserve original behavior: normal videos use up to three B-roll images;
        # Shorts use one image per generated query.
        chosen_queries = queries if is_shorts else queries[:3]
        paths = []
        for index, query in enumerate(chosen_queries):
            print(f"   → [{sid}] Free stock search ({index + 1}/{len(chosen_queries)}): {query}")
            paths.extend(_fetch_images(
                query, sid, images_dir, count=1, orientation=orientation,
                img_num_start=index, topic_hint=topic_hint,
            ))
        image_map[sid] = paths if paths else (None if not is_shorts else [])
        print(f"         saved {len(paths)} image(s)")

    return image_map
