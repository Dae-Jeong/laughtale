# Active Tasks

이 디렉터리는 현재 논의하거나 구현 중인 작업만 보관합니다.

- 작업 하나당 `tasks/<work>.md` 한 파일만 사용합니다.
- 목표, 결정, 시각화, 체크리스트, 검증 결과를 그 파일 안에서 함께 관리합니다.
- 완료 후 재사용할 기준만 `docs/`로 승격하고 task 파일은 삭제합니다.
- 보류한 작업은 `.ideas/`로 요약해 강등하거나 삭제합니다.
- 전체 생명주기는 [`docs/README.md`](../docs/README.md)를 따릅니다.

## Active

- [`linky-chat-internal-dm.md`](linky-chat-internal-dm.md) — 공통 기반·[PostgreSQL Primary/Replica와 서비스 기반 1차 검증](linky-chat-internal-dm.md#postgresql-준비-task--2026-09-08) 완료, 채팅 업무 구현은 후속입니다. 목표 구조·ERD·실시간/복구·부하 검증 설계와 다음에 검토할 한계를 함께 관리합니다.
- [`k3s-bootstrap.md`](k3s-bootstrap.md) — 로컬 K3s, Traefik, Next.js 최소 실행 경로
- [`criteria-governance.md`](criteria-governance.md) — 대화에서 실행 가능한 기준·검증·SoT까지의 연결 구조

공통 템플릿·로깅 설계는 [Backend Template](../external/backend-template/design/README.md)으로 이관했습니다. 이곳의 활성 작업으로 병행 관리하지 않습니다.
