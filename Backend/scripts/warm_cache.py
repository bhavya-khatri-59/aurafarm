"""Sends photos through a running AuraFarm server so their replies are cached, e.g. before a demo.

Usage (from Backend/, with the server running):
  python -m scripts.warm_cache --email you@example.com --password ... demo_photos/*.jpg
Options: --server http://localhost:8000  --lat 12.97 --lon 77.59  --delay 20

Each photo goes into its own new conversation (titled by its diagnosis) in that account. The
delay between photos keeps under the LLM rate limit; a rate-limited photo is retried once.
"""

import argparse
import json
import mimetypes
import sys
import time
from pathlib import Path

import httpx


def send_photo(client: httpx.Client, path: Path, lat: float | None, lon: float | None) -> dict:
    conversation_id = client.post("/conversations", json={}).json()["id"]
    content_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    upload = client.post("/uploads", files={"image": (path.name, path.read_bytes(), content_type)})
    upload.raise_for_status()
    body = {"image_id": upload.json()["id"]}
    if lat is not None and lon is not None:
        body.update(lat=lat, lon=lon)
    events = {}
    with client.stream("POST", f"/conversations/{conversation_id}/messages", json=body, timeout=180) as response:
        response.raise_for_status()
        event = None
        for line in response.iter_lines():
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:") and event in {"diagnosis", "message", "done", "error"}:
                events[event] = json.loads(line[5:])
    return events


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("photos", nargs="+", type=Path)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--server", default="http://localhost:8000")
    parser.add_argument("--lat", type=float)
    parser.add_argument("--lon", type=float)
    parser.add_argument("--delay", type=float, default=20, help="seconds between photos")
    args = parser.parse_args()

    with httpx.Client(base_url=args.server, timeout=60) as client:
        login = client.post("/auth/login", json={"email": args.email, "password": args.password})
        if login.status_code != 200:
            sys.exit(f"Login failed: {login.text}")
        client.headers["Authorization"] = f"Bearer {login.json()['access_token']}"

        failures = 0
        for i, path in enumerate(args.photos):
            if i:
                time.sleep(args.delay)
            events = send_photo(client, path, args.lat, args.lon)
            if "error" in events and "busy" in events["error"].get("detail", ""):
                print(f"rate limited, retrying {path.name} in 60 s")
                time.sleep(60)
                events = send_photo(client, path, args.lat, args.lon)
            if "error" in events:
                failures += 1
                print(f"FAIL  {path.name}: {events['error'].get('detail')}")
                continue
            name = events.get("diagnosis", {}).get("name", "no diagnosis")
            print(f"OK    {path.name}: {name}")
    print(f"\nDone: {len(args.photos) - failures} cached, {failures} failed. Check with: python -m scripts.cache list")


if __name__ == "__main__":
    main()
