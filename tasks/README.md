# Active Tasks

이 디렉터리는 현재 논의하거나 구현 중인 작업만 보관합니다.

- 작업 하나당 `tasks/<work>.md` 한 파일만 사용합니다.
- 목표, 결정, 시각화, 체크리스트, 검증 결과를 그 파일 안에서 함께 관리합니다.
- 완료 후 재사용할 기준만 `docs/`로 승격하고 task 파일은 삭제합니다.
- 보류한 작업은 `.ideas/`로 요약해 강등하거나 삭제합니다.
- 전체 생명주기는 [`docs/README.md`](../docs/README.md)를 따릅니다.

## Active

- [`logging-design-review.md`](logging-design-review.md) — 로깅 구조·대안·기업 레퍼런스의 사용자 판단용 문서이며 FastAPI 템플릿 작업과 연결됩니다.
- [`fastapi-template-prototype.md`](fastapi-template-prototype.md) — FastAPI 함수·DI 흐름과 Compose·환경변수의 로컬 템플릿 초안
- [`linky-chat-internal-dm.md`](linky-chat-internal-dm.md) — 합성 사용자 두 명의 첫 내부 DM vertical slice 명세
- [`k3s-bootstrap.md`](k3s-bootstrap.md) — 로컬 K3s, Traefik, Next.js 최소 실행 경로
- [`criteria-governance.md`](criteria-governance.md) — 대화에서 실행 가능한 기준·검증·SoT까지의 연결 구조
