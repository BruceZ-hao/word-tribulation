import argparse
import csv
import json
from pathlib import Path


def normalize_entry(word: str, phonetic: str, meaning: str):
    word = (word or "").strip().lower()
    phonetic = (phonetic or "").strip() or "-"
    meaning = (meaning or "").strip()

    if not word or not meaning:
        return None
    if not word.replace("-", "").replace("'", "").isalpha():
        return None

    return {"w": word, "p": phonetic, "m": meaning}


def load_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            rows.append(
                normalize_entry(
                    row.get("word") or row.get("sw") or row.get("headword"),
                    row.get("phonetic") or row.get("phone") or row.get("pronunciation"),
                    row.get("translation") or row.get("definition") or row.get("meaning"),
                )
            )
        return [row for row in rows if row]


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        if isinstance(data.get("words"), list):
            data = data["words"]
        elif isinstance(data.get("entries"), list):
            data = data["entries"]
        else:
            raise ValueError("JSON must be an array or contain 'words'/'entries'")

    if not isinstance(data, list):
        raise ValueError("JSON root must be a list")

    entries = []
    for item in data:
        if not isinstance(item, dict):
            continue
        entries.append(
            normalize_entry(
                item.get("w") or item.get("word") or item.get("headword"),
                item.get("p") or item.get("phonetic") or item.get("pronunciation"),
                item.get("m") or item.get("translation") or item.get("definition") or item.get("meaning"),
            )
        )
    return [entry for entry in entries if entry]


def dedupe(entries):
    seen = set()
    result = []
    for entry in entries:
        key = entry["w"]
        if key in seen:
            continue
        seen.add(key)
        result.append(entry)
    return result


def bucket_for_length(length: int):
    if length <= 4:
        return 0
    if length <= 5:
        return 1
    if length <= 7:
        return 2
    if length <= 8:
        return 3
    if length <= 9:
        return 4
    return 5


def group_entries(entries):
    groups = [[] for _ in range(6)]
    for entry in entries:
        groups[bucket_for_length(len(entry["w"]))].append(entry)
    return groups


def main():
    parser = argparse.ArgumentParser(description="Convert ECDICT data into game-ready JSON.")
    parser.add_argument("input", type=Path, help="Path to ECDICT CSV or JSON")
    parser.add_argument("output", type=Path, help="Path to output JSON")
    parser.add_argument("--limit", type=int, default=0, help="Optional max number of words to keep")
    parser.add_argument("--grouped", action="store_true", help="Output 6 realm buckets instead of a flat list")
    args = parser.parse_args()

    suffix = args.input.suffix.lower()
    if suffix == ".csv":
        entries = load_csv(args.input)
    elif suffix == ".json":
        entries = load_json(args.input)
    else:
        raise ValueError("Only .csv and .json are supported")

    entries = dedupe(entries)
    if args.limit > 0:
        entries = entries[: args.limit]

    output = group_entries(entries) if args.grouped else entries

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"wrote {len(entries)} entries to {args.output}")


if __name__ == "__main__":
    main()
