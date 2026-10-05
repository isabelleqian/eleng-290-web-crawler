"""Load the 12 research study areas and their aliases."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from news_importer.errors import ImporterError

DEFAULT_STUDY_AREAS_PATH = Path(__file__).with_name("study_areas.json")
_KINDS = {"city", "state"}


@dataclass(frozen=True)
class StudyArea:
    id: str
    name: str
    kind: str
    aliases: tuple[str, ...]

    @property
    def display_name(self) -> str:
        if self.kind == "state":
            return f"{self.name} (state)"
        return self.name


@dataclass(frozen=True)
class Catalog:
    areas: tuple[StudyArea, ...]
    by_id: dict[str, StudyArea]
    path: Path

    def __init__(self, areas: tuple[StudyArea, ...], aliases: dict[str, str], path: Path):
        object.__setattr__(self, "areas", areas)
        object.__setattr__(self, "by_id", {area.id: area for area in areas})
        object.__setattr__(self, "_aliases", aliases)
        object.__setattr__(self, "path", path)

    def resolve(self, value: str) -> StudyArea | None:
        area_id = self._aliases.get(alias_key(value))
        if area_id is None:
            return None
        return self.by_id[area_id]


def alias_key(value: str) -> str:
    """Fold case, spacing, and dots so NYC, N.Y.C., and nyc match."""
    text = value.strip().casefold().replace(".", "")
    return re.sub(r"\s+", " ", text)


def load_catalog(path: str | Path | None = None) -> Catalog:
    config_path = DEFAULT_STUDY_AREAS_PATH if path is None else Path(path).expanduser()
    if not config_path.is_file():
        raise ImporterError(f"study area configuration not found: {config_path}")
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        raise ImporterError(
            f"study area configuration is not valid UTF-8 ({config_path}): {exc.reason}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise ImporterError(
            f"study area configuration is not valid JSON ({config_path}): {exc.msg}"
        ) from exc

    entries = _entries(payload, config_path)
    areas: list[StudyArea] = []
    aliases: dict[str, str] = {}
    seen_ids: set[str] = set()
    for index, entry in enumerate(entries, start=1):
        area = _parse_area(entry, index, config_path)
        if area.id in seen_ids:
            raise ImporterError(
                f"duplicate study area id '{area.id}' in {config_path}"
            )
        seen_ids.add(area.id)
        areas.append(area)
        for label in (area.id, area.name, *area.aliases):
            key = alias_key(label)
            if key == "":
                raise ImporterError(
                    f"study area '{area.id}' in {config_path} has an empty alias"
                )
            previous = aliases.get(key)
            if previous is not None and previous != area.id:
                raise ImporterError(
                    f"study area alias '{label}' in {config_path} matches both "
                    f"'{previous}' and '{area.id}'"
                )
            aliases[key] = area.id
    return Catalog(tuple(areas), aliases, config_path)


def _entries(payload: object, path: Path) -> list[object]:
    if not isinstance(payload, dict) or not isinstance(payload.get("study_areas"), list):
        raise ImporterError(
            f"study area configuration {path} must contain a study_areas list"
        )
    return payload["study_areas"]


def _parse_area(entry: object, index: int, path: Path) -> StudyArea:
    if not isinstance(entry, dict):
        raise ImporterError(f"study area #{index} in {path} must be an object")
    area_id = entry.get("id")
    name = entry.get("name")
    kind = entry.get("kind")
    aliases = entry.get("aliases")
    if not isinstance(area_id, str) or area_id.strip() == "":
        raise ImporterError(f"study area #{index} in {path} needs a nonblank id")
    if not isinstance(name, str) or name.strip() == "":
        raise ImporterError(f"study area '{area_id}' in {path} needs a name")
    if kind not in _KINDS:
        raise ImporterError(
            f"study area '{area_id}' in {path} has kind '{kind}'; use city or state"
        )
    if not isinstance(aliases, list) or not all(isinstance(item, str) for item in aliases):
        raise ImporterError(f"study area '{area_id}' in {path} needs a list of aliases")
    return StudyArea(
        id=area_id.strip(),
        name=name.strip(),
        kind=kind,
        aliases=tuple(aliases),
    )
