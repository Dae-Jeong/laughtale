#!/usr/bin/env python3
"""Render local Laughtale ideas and tasks as an Orca-viewable Markdown snapshot."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class Category:
    key: str
    label: str
    directory: str
    show_progress: bool = False


CATEGORIES = {
    "ideas": Category("ideas", "Ideas", ".ideas"),
    "tasks": Category("tasks", "Tasks", "tasks", show_progress=True),
}

TITLE_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
STATUS_RE = re.compile(r"^Status:\s*(.+?)\s*$", re.MULTILINE | re.IGNORECASE)
CHECKBOX_RE = re.compile(r"^\s*-\s*\[([ xX])\]", re.MULTILINE)
SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)

CONTEXT_SECTIONS = {
    "ideas": ("현재 결론", "현재 생각", "현재 가정", "목표"),
    "tasks": ("현재 상태", "확정한 선택"),
}

NEXT_SECTIONS = {
    "ideas": (
        "다시 검토할 시점",
        "별도 오픈소스로 승격하는 조건",
        "결정이 필요한 항목",
        "다음 단계 후보",
    ),
    "tasks": ("열린 판단", "결정이 필요한 항목"),
}


def find_project_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    return current


def first_summary(text: str) -> str:
    in_fence = False
    paragraph: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if not line:
            if paragraph:
                break
            continue
        if (
            line.startswith(("#", "-", "|", ">"))
            or re.match(r"^\d+\.\s", line)
            or line.lower().startswith(("status:", "checked:"))
        ):
            continue
        paragraph.append(line)

    return " ".join(paragraph) if paragraph else "설명이 없습니다."


def markdown_sections(text: str) -> dict[str, str]:
    matches = list(SECTION_RE.finditer(text))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group(1).strip()] = text[start:end].strip()
    return sections


def clip(text: str, limit: int = 360) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def section_preview(
    sections: dict[str, str],
    candidates: tuple[str, ...],
    *,
    prefer_items: bool = False,
) -> str | None:
    for heading in candidates:
        body = sections.get(heading)
        if not body:
            continue

        in_fence = False
        items: list[str] = []
        paragraph: list[str] = []
        for raw_line in body.splitlines():
            line = raw_line.strip()
            if line.startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence or line.startswith(("#", "|")):
                continue
            if not line:
                if paragraph and not prefer_items:
                    break
                continue

            item_match = re.match(r"^(?:[-*+]\s+|\d+\.\s+)(.+)$", line)
            if item_match:
                items.append(item_match.group(1).strip())
                if len(items) == 2:
                    break
                continue

            if not items:
                paragraph.append(line)

        if items:
            return clip(" / ".join(items))
        if paragraph:
            return clip(" ".join(paragraph))
    return None


def read_entries(root: Path, category: Category) -> list[dict[str, object]]:
    directory = root / category.directory
    if not directory.is_dir():
        return []

    entries: list[dict[str, object]] = []
    for path in sorted(directory.glob("*.md"), key=lambda item: item.name.lower()):
        if path.name.lower() == "readme.md":
            continue

        text = path.read_text(encoding="utf-8")
        title_match = TITLE_RE.search(text)
        status_match = STATUS_RE.search(text)
        checks = CHECKBOX_RE.findall(text) if category.show_progress else []
        completed = sum(mark.lower() == "x" for mark in checks)
        sections = markdown_sections(text)

        entries.append(
            {
                "title": title_match.group(1).strip() if title_match else path.stem,
                "status": status_match.group(1).strip() if status_match else "미기재",
                "summary": first_summary(text),
                "path": path.relative_to(root).as_posix(),
                "completed": completed,
                "total": len(checks),
                "context": section_preview(sections, CONTEXT_SECTIONS[category.key]),
                "next": section_preview(
                    sections,
                    NEXT_SECTIONS[category.key],
                    prefer_items=True,
                ),
            }
        )
    return entries


def progress_text(entry: dict[str, object]) -> str:
    return (
        f"{entry['completed']}/{entry['total']}"
        if entry["total"]
        else "체크리스트 없음"
    )


def render_category(category: Category, entries: list[dict[str, object]]) -> list[str]:
    lines = [f"## {category.label} ({len(entries)})", ""]
    if not entries:
        return [*lines, "현재 항목이 없습니다.", ""]

    if category.show_progress:
        lines.extend(
            [
                "| 이름 | 상태 | 진행 | 설명 |",
                "| --- | --- | --- | --- |",
            ]
        )
        for entry in entries:
            lines.append(
                f"| [{entry['title']}](../{entry['path']}) | {entry['status']} | "
                f"{progress_text(entry)} | {entry['summary']} |"
            )
    else:
        lines.extend(
            [
                "| 이름 | 상태 | 설명 |",
                "| --- | --- | --- |",
            ]
        )
        for entry in entries:
            lines.append(
                f"| [{entry['title']}](../{entry['path']}) | {entry['status']} | "
                f"{entry['summary']} |"
            )
    return [*lines, ""]


def render_snapshot(
    root: Path,
    selected: list[Category],
    collected: dict[str, list[dict[str, object]]],
) -> str:
    counts = {key: len(entries) for key, entries in collected.items()}

    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")
    lines = [
        "# Project Status",
        "",
        f"Generated: {generated_at}",
        "",
        "```mermaid",
        "flowchart LR",
    ]
    lines.append('    STATUS["Laughtale Status"]')
    for category in selected:
        lines.append(
            f'    STATUS --> {category.key.upper()}["{category.label} · {counts[category.key]}"]'
        )
    lines.extend(["```", ""])

    for category in selected:
        lines.extend(render_category(category, collected[category.key]))

    lines.extend(
        [
            "---",
            "",
            "이 파일은 생성된 로컬 스냅샷입니다. 원본은 `.ideas/`와 `tasks/`에 있습니다.",
            "",
        ]
    )
    return "\n".join(lines)


def render_chat_summary(
    root: Path,
    selected: list[Category],
    collected: dict[str, list[dict[str, object]]],
    output: Path,
) -> str:
    lines: list[str] = []
    for category in selected:
        entries = collected[category.key]
        lines.extend([f"## {category.label} ({len(entries)})", ""])
        if not entries:
            lines.extend(["현재 항목이 없습니다.", ""])
            continue

        for entry in entries:
            source_path = (root / str(entry["path"])).as_posix()
            metadata = f"`{entry['status']}`"
            if category.show_progress:
                metadata += f" · 진행 {progress_text(entry)}"
            lines.extend(
                [
                    f"### [{entry['title']}]({source_path})",
                    "",
                    f"- 상태: {metadata}",
                    f"- 요약: {entry['summary']}",
                    *(
                        [f"- 현재: {entry['context']}"]
                        if entry["context"]
                        else []
                    ),
                    *(
                        [
                            f"- {'다음 판단' if category.show_progress else '다시 볼 때'}: "
                            f"{entry['next']}"
                        ]
                        if entry["next"]
                        else []
                    ),
                    "",
                ]
            )

    lines.append(f"[Mermaid와 상세 현황 보기]({output.as_posix()})")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", choices=("all", *CATEGORIES), default="all")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, default=Path(".status/project-status.md"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = find_project_root(args.root)
    selected = list(CATEGORIES.values()) if args.kind == "all" else [CATEGORIES[args.kind]]
    collected = {category.key: read_entries(root, category) for category in selected}
    content = render_snapshot(root, selected, collected)

    output = args.output if args.output.is_absolute() else root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")

    print(render_chat_summary(root, selected, collected, output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
