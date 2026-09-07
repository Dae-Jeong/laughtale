# Persistence — Repository와 트랜잭션

읽는 때: DB 조회·저장·ORM 매핑·migration·원자성·경합 처리를 변경할 때 읽습니다.
공통 기준과 문서 선택은 [개발 규칙 진입점](../engineering-principles.md)을 따릅니다.

## Repository

- 업무 의미가 있는 조회·저장 계약을 제공하며 쿼리와 영속화를 담당합니다. 업무 정책이나 HTTP 오류 응답을 결정하지 않습니다.
- Domain 모델 또는 명시적인 조회 결과 타입을 반환합니다. ORM 객체는 영속화 구현 내부에 유지하고 필요한 데이터는 이 경계에서 확보합니다. 집계·projection 등 결과 형태가 다를 때 별도 조회 DTO를 사용합니다.
- 저장·upsert 입력은 Domain 모델이나 명시적인 타입으로 표현하며 호출자가 만든 임의 dict로 영속화 필드를 전달하지 않습니다.
- 조회에는 계약이 요구하는 소유자·scope 조건을 포함합니다. pagination의 정렬·조회 조건은 Repository가 소유합니다.
- DB 문자열을 Enum으로 다룰 경우 로딩 시 실제 변환과 잘못된 값 처리를 검증합니다. 타입 annotation만으로 런타임 변환을 가정하지 않습니다.
- 인덱스·제약을 중복 정의하지 않으며 schema 변경과 migration을 함께 검토합니다.

## 트랜잭션과 외부 실행

- Service 또는 Facade의 Application use case 경계에서 원자성 범위를 정합니다. 같은 프로세스·DB의 단일 원자적 작업에 참여하는 Service들은 공통 트랜잭션을 사용합니다. transaction manager/Unit of Work가 commit·rollback·cleanup을 책임지고 참여 Service·Repository가 중간에 독립 commit하지 않습니다.
- 독립 backend 서비스·DB를 조합할 때 로컬 트랜잭션으로 전체 원자성을 보장한다고 가정하지 않습니다. 단계별 트랜잭션과 재시도·보상·재개 정책을 정합니다.
- DB 읽기도 세션 수명과 필요한 일관성 수준을 명시합니다. 특정 데코레이터·전역 SessionProxy를 필수로 하지 않습니다. 명시적 세션 주입도 사용할 수 있습니다.
- 한 DB 세션을 여러 비동기 task가 동시에 사용하지 않습니다. 병렬 DB 작업에는 독립 세션·트랜잭션을 사용하고 달라지는 전체 원자성을 설계에 반영합니다.
- 외부 응답 대기·polling·streaming 동안 DB 트랜잭션을 열어 두지 않습니다. 상태 기록, 외부 실행, 결과 반영을 짧은 단계로 나누고 실패·재개 조건을 정의합니다.
- DB 변경과 이벤트 전달을 함께 보장해야 할 때 outbox 등 복구 가능한 방식을 검토합니다. 단순 after-commit 호출만으로 전달 보장을 주장하지 않습니다.
- 독립 트랜잭션에는 세션에 묶인 ORM 객체 대신 식별자·값을 전달합니다. savepoint와 독립 commit은 실패 전파 범위를 정한 경우에만 사용합니다.
- flush는 생성 값 확보, 제약 위반 감지, 후속 조회 가시성이 필요할 때 수행하며 commit으로 취급하지 않습니다.
- 제약·잠금·조건부 갱신으로 경합을 처리합니다. 먼저 조회한 결과만으로 중복·한도 위반을 막았다고 가정하지 않습니다.
- 취소·예외 시 rollback과 자원 반환을 보장하며 cleanup 오류가 원래 실패를 덮지 않게 합니다.

## 함께 읽을 조건

- 금액·시간·Enum의 저장·로딩에서 업무 값의 의미를 적용하면 [Domain](domain.md)을 읽습니다.
- cursor 형식·공개 응답을 바꾸면 [HTTP API](http-api.md)를 읽습니다.
- 외부 통신 자체를 변경하면 [외부 연계](external-integrations.md)를 읽습니다.
- DB 격리·회귀·경합 검증은 [Testing](testing.md)을 읽습니다.
