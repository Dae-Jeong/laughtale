# 로깅 설계 — 정본 참조

Status: transferred · 2026-09-07

Backend Template의 설계 정본은 [Dae-Jeong/backend-template](https://github.com/Dae-Jeong/backend-template)입니다.

- [설계 안내와 소유권](https://github.com/Dae-Jeong/backend-template/blob/main/design/README.md)
- [개발 원칙](https://github.com/Dae-Jeong/backend-template/blob/main/design/engineering.md)
- [공통 로깅·관측](https://github.com/Dae-Jeong/backend-template/blob/main/design/observability.md)
- [FastAPI 구현 설계](https://github.com/Dae-Jeong/backend-template/blob/main/design/implementations/fastapi.md)
- [초기화·종료 검증](https://github.com/Dae-Jeong/backend-template/blob/main/design/implementations/fastapi-verification.md)

공용 로깅 계약은 새 저장소가 소유합니다. Laughtale의 행위자·채팅 이벤트·감사 이력은 필요한 기능 설계에서 별도로 정의합니다.
기존 본문은 정본과 중복 관리하지 않습니다. 코드 구현 완료를 뜻하지 않습니다.
