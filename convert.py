import json
import re
from pathlib import Path
TEMP_ROOT = Path(__file__).resolve().parent / "results"

INPUT_PATH = TEMP_ROOT / "cbom_output.json"
OUTPUT_PATH = TEMP_ROOT / "cbom_iso_output.json"

def clean_output_string(raw: str) -> str:
    raw = raw.strip()

    raw = re.sub(r"^```json", "", raw, flags=re.IGNORECASE).strip()
    raw = re.sub(r"^```", "", raw).strip()
    raw = re.sub(r"```$", "", raw).strip()

    return raw


def extract_cbom_objects(data: list) -> list:
    results = []

    for entry in data:
        output_text = entry.get("output", "").strip()
        if not output_text:
            continue

        cleaned = clean_output_string(output_text)

        try:
            parsed = json.loads(cleaned)
            results.append(parsed)
        except json.JSONDecodeError:
            print("Skipping invalid JSON:", output_text[:80], "...")
            continue

    return results


if __name__ == "__main__":
    raw_data = json.loads(Path(INPUT_PATH).read_text())

    cbom_objects = extract_cbom_objects(raw_data)

    Path(OUTPUT_PATH).write_text(
        json.dumps(cbom_objects, indent=4)
    )

    print(f"Extracted {len(cbom_objects)} CBOM objects → {OUTPUT_PATH}")
