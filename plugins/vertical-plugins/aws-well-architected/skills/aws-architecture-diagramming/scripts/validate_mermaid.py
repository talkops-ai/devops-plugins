#!/usr/bin/env python3
"""Deterministic validator for Mermaid blocks (in .md/.mmd files) and .drawio XML files.

Usage:
    python3 validate_mermaid.py <path-to-file.drawio|file.mmd|file.md> [...]
"""

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SUPPORTED_MERMAID_HEADERS = (
    "flowchart ",
    "graph ",
    "sequenceDiagram",
    "stateDiagram",
    "stateDiagram-v2",
    "classDiagram",
    "erDiagram",
    "xychart-beta",
)

UNQUOTED_PAREN_NODE_RE = re.compile(r"\b[A-Za-z0-9_-]+\[[^\"\]\n]*[()][^\"\]\n]*\]")
HTML_TAG_RE = re.compile(r"<(?:br|b|i|div|span|p)\b[^>\n]*>", re.I)


def validate_drawio(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    if "<!--" in text:
        for match in re.finditer(r"<!--(.*?)-->", text, re.S):
            if "--" in match.group(1):
                errors.append(f"{path}: XML comment contains illegal double-hyphen '--'")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        errors.append(f"{path}: XML parse error: {exc}")
        return errors

    if root.tag != "mxfile":
        errors.append(f"{path}: root element must be <mxfile>, found <{root.tag}>")
        return errors

    cells = root.findall(".//mxCell")
    if len(cells) < 3:
        errors.append(f"{path}: diagram contains fewer than 3 <mxCell> elements")
    seen_ids: set[str] = set()
    for cell in cells:
        cid = cell.attrib.get("id")
        if not cid:
            errors.append(f"{path}: <mxCell> missing 'id' attribute")
        elif cid in seen_ids:
            errors.append(f"{path}: duplicate mxCell id='{cid}'")
        else:
            seen_ids.add(cid)
    for req_id in ("0", "1"):
        if req_id not in seen_ids:
            errors.append(f"{path}: missing root structural mxCell id='{req_id}'")
    return errors


def validate_mermaid_block(block: str, where: str) -> list[str]:
    errors: list[str] = []
    lines = [ln.strip() for ln in block.strip().splitlines() if ln.strip() and not ln.strip().startswith("%%")]
    if not lines:
        errors.append(f"{where}: empty mermaid block")
        return errors
    first = lines[0]
    if not first.startswith(SUPPORTED_MERMAID_HEADERS):
        errors.append(
            f"{where}: unsupported or missing Mermaid diagram header '{first}'. "
            f"Use one of: {', '.join(SUPPORTED_MERMAID_HEADERS)}"
        )
    for idx, line in enumerate(lines[1:], start=2):
        if UNQUOTED_PAREN_NODE_RE.search(line):
            errors.append(f"{where} (line {idx}): unquoted parentheses in node label `{line}` — wrap label in quotes `id[\"Label (info)\"]`")
        if HTML_TAG_RE.search(line):
            errors.append(f"{where} (line {idx}): HTML tag found in Mermaid line `{line}` — avoid HTML tags")
    return errors


def validate_file(path: Path) -> list[str]:
    if not path.is_file():
        return [f"{path}: file not found"]
    ext = path.suffix.lower()
    if ext == ".drawio" or ext == ".xml":
        return validate_drawio(path)
    text = path.read_text(encoding="utf-8", errors="replace")
    if ext in (".mmd", ".mermaid"):
        return validate_mermaid_block(text, str(path))
    blocks = re.findall(r"```mermaid\s*\n(.*?)```", text, re.S)
    errs: list[str] = []
    for i, blk in enumerate(blocks, start=1):
        errs.extend(validate_mermaid_block(blk, f"{path}#mermaid-{i}"))
    return errs


def main(argv: list[str]) -> int:
    if not argv:
        print("Usage: validate_mermaid.py <file.drawio|file.mmd|file.md> [...]", file=sys.stderr)
        return 2
    all_errors: list[str] = []
    for arg in argv:
        all_errors.extend(validate_file(Path(arg)))
    if all_errors:
        for err in all_errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1
    print(f"VALIDATION PASSED ({len(argv)} file(s) checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
