"""Naming and object type rules for a BACnet point list.

Naming convention checked: BUILDING.EQUIPNN.POINT, all upper case, for example
BLDGA.AHU01.SAT. The equipment segment is a letter code followed by two digits.
"""

from __future__ import annotations

import csv
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

OBJECT_TYPES = {"AI", "AO", "AV", "BI", "BO", "BV", "MSI", "MSO", "MSV"}
ANALOG = {"AI", "AO", "AV"}
MAX_INSTANCE = 4194302

NAME_PATTERN = re.compile(r"^[A-Z0-9]{2,8}\.[A-Z]{2,5}\d{2}\.[A-Z][A-Z0-9_]{1,20}$")
EQUIP_SEGMENT = re.compile(r"^[A-Z]+(\d*)$")

# Last name segment suffix -> object types that suit it.
SUFFIX_TYPES: dict[str, set[str]] = {
    "SAT": {"AI"}, "RAT": {"AI"}, "OAT": {"AI"}, "MAT": {"AI"}, "ZNT": {"AI"},
    "SP": {"AV", "AO"}, "CMD": {"AO", "BO"}, "STS": {"BI", "BV", "MSI"},
    "ALM": {"BI", "BV"},
}


@dataclass(frozen=True)
class Finding:
    """One lint result tied to a CSV line (the header is line 1)."""

    line: int
    rule: str
    name: str
    message: str

    def __str__(self) -> str:
        return f"line {self.line} {self.rule} [{self.name or '-'}] {self.message}"


def allowed_types(last_segment: str) -> set[str] | None:
    """Return the object types that suit a point suffix, or None when the suffix is unknown."""
    for suffix, types in SUFFIX_TYPES.items():
        if last_segment == suffix or last_segment.endswith("_" + suffix):
            return types
    return None


def lint_rows(rows: Iterable[dict[str, str]], max_length: int = 32) -> list[Finding]:
    """Lint rows with columns object_type, instance, name, units."""
    rows = list(rows)
    findings: list[Finding] = []
    names = Counter((r.get("name") or "").strip().upper() for r in rows)
    objects = Counter(
        ((r.get("object_type") or "").strip().upper(), (r.get("instance") or "").strip())
        for r in rows
    )

    for number, row in enumerate(rows, start=2):
        name = (row.get("name") or "").strip()
        otype = (row.get("object_type") or "").strip().upper()
        instance = (row.get("instance") or "").strip()
        units = (row.get("units") or "").strip()

        def add(rule: str, message: str, number: int = number, name: str = name) -> None:
            findings.append(Finding(number, rule, name, message))

        if otype not in OBJECT_TYPES:
            add("B005", f"object type '{otype}' is not a known BACnet type")
        if not instance.isdigit() or int(instance) > MAX_INSTANCE:
            add("B011", f"instance '{instance}' must be a whole number from 0 to {MAX_INSTANCE}")
        elif objects[(otype, instance)] > 1:
            add("B004", f"{otype} {instance} is used more than once")
        if otype in ANALOG and not units:
            add("B008", "analog object has no units")

        if not name:
            add("B001", "point has no name")
            continue
        upper = name.upper()
        if names[upper] > 1:
            add("B003", "name duplicated (case-insensitive)")
        if re.search(r"\s", name):
            add("B002", "name contains whitespace")
        if name != upper:
            add("B010", "name is not all upper case")
        if len(name) > max_length:
            add("B009", f"name is {len(name)} characters, limit is {max_length}")

        parts = upper.split(".")
        equip = EQUIP_SEGMENT.match(parts[1]) if len(parts) > 1 else None
        if equip and len(equip.group(1)) != 2 and len(parts) == 3:
            add("B007", f"equipment number in '{parts[1]}' needs exactly two digits")
        elif not NAME_PATTERN.match(upper):
            add("B001", "name does not match BUILDING.EQUIPNN.POINT")

        allowed = allowed_types(parts[-1])
        if allowed and otype in OBJECT_TYPES and otype not in allowed:
            add("B006", f"suffix suggests {'/'.join(sorted(allowed))}, found {otype}")
    return findings


def lint_file(path: str | Path, max_length: int = 32) -> list[Finding]:
    """Read a CSV file and lint it."""
    with open(path, newline="", encoding="utf-8") as handle:
        return lint_rows(csv.DictReader(handle), max_length)
