import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

# Run this from repo root: `python scripts/preseed_voice_previews.py`

def main():
    # Don't echo secrets; just ensure we have a key if needed for synthesis
    key_present = bool(os.getenv("OPENAI_API_KEY"))
    if not key_present:
        print("OPENAI_API_KEY not set. Only existing cached/static previews will be available.")

    # Ensure repo root on path for `import app`
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    # Lazy import to avoid side effects during packaging
    from app.main import app

    out_dir = Path("app/static/voices")
    out_dir.mkdir(parents=True, exist_ok=True)

    client = TestClient(app)

    # Load catalog
    r = client.get("/voices")
    r.raise_for_status()
    voices = r.json()
    print(f"Found {len(voices)} voices in catalog")

    for v in voices:
        vid = v.get("id")
        if not vid:
            continue
        target = out_dir / f"{vid}-preview.mp3"
        if target.exists() and target.stat().st_size > 0:
            print(f"✔ {vid}: cached ({target})")
            continue
        print(f"… {vid}: generating")
        # Call the same internal endpoint used by the UI; this will synthesize and cache to disk
        resp = client.get(f"/voices/preview/{vid}")
        if resp.status_code != 200:
            print(f"  ! {vid}: failed ({resp.status_code} {resp.text})")
            continue
        # Response already wrote to disk; ensure file exists
        if not target.exists():
            # As a fallback write the content from the response
            with open(target, "wb") as f:
                f.write(resp.content)
        size = target.stat().st_size if target.exists() else 0
        print(f"  ↳ wrote {target} ({size} bytes)")

    print("Done.")


if __name__ == "__main__":
    main()
