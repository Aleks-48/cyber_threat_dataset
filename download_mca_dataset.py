"""Fetch the public Mendeley CSV locally and verify it against the recorded digest."""
from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.request import Request, urlopen

URL = "https://data.mendeley.com/public-files/datasets/fktgy52645/files/e56b93dd-136e-42ab-8c76-ac72df62e3dd/file_downloaded"
EXPECTED_SHA256 = "6636a1195a683407e6ce6734430e0713d2b71b6b391a18490e7c1c9c68575b53"
EXPECTED_BYTES = 1_579_284
DEST = Path(__file__).resolve().parent / "analysis" / "external_sources" / "MCA_Russian_Toxic_Comments" / "raw" / "combined.csv"


def main() -> None:
    DEST.parent.mkdir(parents=True, exist_ok=True)
    req = Request(URL, headers={"User-Agent": "local-research-reproducibility/1.0"})
    with urlopen(req, timeout=45) as response:
        payload = response.read(EXPECTED_BYTES + 1)
    digest = hashlib.sha256(payload).hexdigest()
    if len(payload) != EXPECTED_BYTES or digest != EXPECTED_SHA256:
        raise SystemExit(f"Downloaded file did not match expected bytes/SHA-256; got {len(payload)} bytes, {digest}")
    DEST.write_bytes(payload)
    print(f"Verified source file saved locally: {DEST} ({len(payload)} bytes, SHA-256 {digest})")
    print("The CSV contains user-generated text and source URLs. Keep it local; do not publish it.")


if __name__ == "__main__":
    main()

