"""Loads the assumption files in data/assumptions/.

No number used by the calculations lives in the code. Each one sits in a YAML
file as a small record: value, unit, source, date checked, and whether it is
an estimate. This module reads those records.
"""

from functools import lru_cache
from pathlib import Path

import yaml

ASSUMPTIONS_DIR = Path(__file__).resolve().parents[1] / "data" / "assumptions"
FILES = ["vessels", "ports", "market", "costs"]


@lru_cache(maxsize=None)
def load(name: str) -> dict:
    """Read one assumption file, e.g. load("vessels")."""
    with open(ASSUMPTIONS_DIR / f"{name}.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def is_record(node) -> bool:
    return isinstance(node, dict) and "value" in node


def val(node):
    """The value of an assumption record."""
    return node["value"]


def is_estimate(node) -> bool:
    return bool(node.get("estimate", False))


def get(name: str, *path):
    """Shortcut: get("costs", "financing", "margin_pct") returns the value."""
    node = load(name)
    for key in path:
        node = node[key]
    return val(node)


def record(name: str, *path) -> dict:
    """The full record (value, source, estimate flag...) for display."""
    node = load(name)
    for key in path:
        node = node[key]
    return node


def all_records() -> list[dict]:
    """Every assumption as a flat list of rows, for the Methodology page."""
    rows = []

    def walk(node, file, path):
        if is_record(node):
            if "source" in node:  # skip plain labels such as names
                rows.append({
                    "file": f"{file}.yaml",
                    "assumption": " / ".join(path),
                    "value": node["value"],
                    "unit": node.get("unit", ""),
                    "estimate": is_estimate(node),
                    "source": node.get("source", ""),
                    "url": node.get("url", ""),
                    "checked": str(node.get("checked", "")),
                    "note": " ".join(str(node.get("note", "")).split()),
                })
        elif isinstance(node, dict):
            for key, child in node.items():
                walk(child, file, path + [key])

    for file in FILES:
        walk(load(file), file, [])
    return rows


def to_markdown() -> str:
    """The whole assumption book as a Markdown document (docs/ASSUMPTIONS.md)."""
    rows = all_records()
    estimates = sum(r["estimate"] for r in rows)
    lines = [
        "# Assumptions",
        "",
        "Generated from the YAML files in `data/assumptions/`. Do not edit by hand: change the",
        "YAML and run `python -m engine.assumptions`.",
        "",
        f"{len(rows)} assumptions, of which {estimates} are marked **estimated**: our own figures,",
        "published figures used as a proxy, or figures not yet confirmed against their source.",
        "Real traded freight rates and physical price premiums are paywalled, so every ship hire rate",
        "here is an estimate: either our own figure, or a published broker or press figure for another",
        "route or contract used as a proxy (the source column says which). Ship figures read from a",
        "search-engine extract are also marked estimated until confirmed against the document itself.",
    ]
    current_file = None
    for r in rows:
        if r["file"] != current_file:
            current_file = r["file"]
            lines += ["", f"## {current_file}", "",
                      "| Assumption | Value | Unit | Status | Source | Checked | Reasoning and limits |",
                      "|---|---|---|---|---|---|---|"]
        source = f"[{r['source']}]({r['url'].replace(' ', '%20')})" if r["url"] else r["source"]
        status = "**estimated**" if r["estimate"] else "published"
        lines.append(f"| {r['assumption']} | {r['value']} | {r['unit']} | {status} | {source} "
                     f"| {r['checked']} | {r['note']} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    target = ASSUMPTIONS_DIR.parents[1] / "docs" / "ASSUMPTIONS.md"
    target.write_text(to_markdown(), encoding="utf-8")
    print(f"Wrote {target}")
