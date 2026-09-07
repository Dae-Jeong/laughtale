---
name: project-status
description: On explicit request, summarize this Laughtale repository's current ideas and task documents, optionally filtered to ideas or tasks, and write an Orca-viewable Markdown snapshot. Use only for a direct project-status, idea-list, or task-list request. Do not use for routine progress updates, Git status, Kubernetes status, or process monitoring.
---

# Project Status

Show the repository's planning status without changing its source documents.

Run only after an explicit natural-language request for this status or a direct `$project-status` invocation. Do not run proactively while performing another task.

## Modes

- `ideas`: The request asks only for ideas or future candidates.
- `tasks`: The request asks only for current or ongoing tasks.
- `all`: The request asks for project status, both groups, or does not specify a group.

Run from the repository root:

```bash
python3 .agents/skills/project-status/scripts/render_status.py --kind <all|ideas|tasks>
```

The script prints a compact Markdown list for the conversation and writes `.status/project-status.md`. The snapshot contains a Mermaid count overview and tables with title, explicit status, summary, and task checklist progress.

Return the script's Markdown output verbatim in the conversation; do not shorten or rewrite its summaries. Each item shows its title, explicit status, content summary, current context, and a review trigger or open decision when the source provides one. Task progress is included when available. Keep the final snapshot link as an optional detail view; never make opening it necessary to understand the requested items.

The response should follow this shape:

```markdown
## Tasks (2)

### [Task name](/absolute/path/tasks/task-name.md)

- 상태: `proposed` · 진행 2/5
- 요약: 이 task가 해결하려는 내용을 설명합니다.
- 현재: 아직 구현되지 않은 현재 상태를 설명합니다.
- 다음 판단: 작업을 진행하기 전에 결정할 내용을 설명합니다.

[Mermaid와 상세 현황 보기](/absolute/path/.status/project-status.md)
```

Show only the selected mode. Do not replace the list with a count-only response or copy the snapshot's full tables into the response.

## Source rules

- Ideas come from `.ideas/*.md`; tasks come from `tasks/*.md`.
- Exclude each directory's `README.md`.
- Preserve an explicit `Status:` value. Report `미기재` when it is absent; do not infer one.
- Extract context only from explicit sections such as `현재 결론`, `현재 생각`, `현재 상태`, `다시 검토할 시점`, and `열린 판단`; do not invent missing context.
- For tasks, count Markdown checkboxes as progress. A task without checkboxes has no numeric progress.
- Treat missing directories as empty categories.
- Do not create, promote, demote, rename, or edit an idea or task while reporting status.
- Add a new category only after its source directory and lifecycle meaning have been defined in the project.
