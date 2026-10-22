"""Build data/messages.csv and data/tricky.csv from the hand-written templates.

Every template in data/templates/*.json has two variants. Both variants keep the
same template_id, so the notebook can split by template and no template appears
in both train and test. Rules for writing templates: data/templates/SPEC.md.

Run from the project root:  python data/build_dataset.py
The automatic audit (data/audit.py) runs at the end and exits with 1 on failure.
"""
import csv
import json
import re
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent
sys.path.insert(0, str(DATA))  # so `import audit` works from any working directory
import audit  # noqa: E402

TEMPLATES = DATA / "templates"
SOURCES = ["ar_ham", "ar_spam", "en_ham", "en_spam"]
ARABIC_RE = re.compile(r"[؀-ۿ]")


def check_safe(text, label=None):
    """Fail fast, before writing: reserved .example domains, masked phones."""
    for host in audit.hosts(text):
        if not host.endswith(".example"):
            raise ValueError(f"non-reserved domain {host!r} in: {text}")
        if label == "spam" and host in audit.TRUSTED:
            raise ValueError(f"trusted domain {host!r} in spam: {text}")
    if re.search(r"\+\d{2,3}\s?\d{3,}", text):
        raise ValueError(f"unmasked phone in: {text}")


def load_messages():
    rows = []
    for name in SOURCES:
        lang = name.split("_")[0]
        for t in json.loads((TEMPLATES / f"{name}.json").read_text(encoding="utf-8")):
            for text in t["variants"]:
                check_safe(text, t["label"])
                if lang == "en" and ARABIC_RE.search(text):
                    raise ValueError(f"Arabic script in English row: {text}")
                rows.append({"text": text, "lang": lang, "label": t["label"],
                             "category": t["category"], "template_id": t["template_id"]})
    return rows


def load_tricky():
    rows = json.loads((TEMPLATES / "tricky.json").read_text(encoding="utf-8"))
    for r in rows:
        check_safe(r["text"], r["label"])
    return [{k: r[k] for k in ("text", "lang", "label", "why_tricky")} for r in rows]


def write(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{path.name}: {len(rows)} rows")


if __name__ == "__main__":
    messages = load_messages()
    known = {re.sub(r"\d", "0", m["text"]) for m in messages}
    tricky = load_tricky()
    overlap = [r["text"] for r in tricky if re.sub(r"\d", "0", r["text"]) in known]
    if overlap:
        raise ValueError(f"tricky rows also in messages: {overlap}")
    write(DATA / "messages.csv", messages)
    write(DATA / "tricky.csv", tricky)

    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(0 if audit.run() else 1)
