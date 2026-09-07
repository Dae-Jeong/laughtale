# HTTP API — Router와 Schema

읽는 때: endpoint, 요청·응답 DTO, HTTP 오류, pagination 계약을 변경할 때 읽습니다.
공통 기준과 문서 선택은 [개발 규칙 진입점](../engineering-principles.md)을 따릅니다.

## Router / Controller

- HTTP API는 MVC 기반 책임 분리를 적용합니다. FastAPI Router와 Spring Controller는 요청 진입점이며, JSON 응답 표현은 Response DTO·직렬화가 담당합니다. 화면은 프런트엔드가 소유합니다.
- 요청 파싱·형식 검증, 인증 문맥 전달, 단일 Service/Facade use case 호출, 응답 변환을 담당합니다. DB·외부 API를 직접 호출하거나 업무 판단을 하지 않습니다.
- 정책별 호출 대상 선택, 여러 결과의 필터링·합산은 Application에 둡니다. 인증·프로토콜 권한은 API 경계에서, 자원 소유권·업무 한도는 use case에서 검증합니다.

## DTO와 응답

- Request는 외부 입력, Response는 공개 표현을 소유합니다. Service에는 HTTP 프레임워크 객체를 전달하지 않습니다.
- 전송 계층 의존이 없고 업무 입력과 의미가 같은 값 Schema는 그대로 전달할 수 있습니다. HTTP 전용 변환이나 의미 차이가 있을 때만 내부 입력으로 변환합니다.
- 응답 변환은 표현만 바꾸며 조회·lazy loading·업무 판단·상태 변경을 하지 않습니다. ORM 객체나 임의의 내부 dict를 API 응답으로 그대로 노출하지 않습니다.
- Router는 `from_internal()` 같은 명시적 변환을 사용합니다. 내부 모델을 내부 DTO로 바꾸는 `from_entity()`는 Application에서 사용하며 Router에서 호출하지 않습니다.
- JSON 필드 casing, 성공·오류 표현, pagination은 서비스 API 계약에서 일관되게 정합니다. cursor 형식·직렬화는 Schema/codec이 소유합니다.
- 업무·외부 연계의 내부 오류를 HTTP status와 공개 code·사용자용 message로 변환합니다. 외부 오류 원문을 공개 응답에 그대로 노출하지 않으며 request ID로 로그와 연결합니다.

## 함께 읽을 조건

- 날짜·금액·상태 값의 변환에 업무 기준을 적용하면 [Domain](domain.md)을 읽습니다.
- use case의 입력·반환·업무 권한이 바뀌면 [Application](application.md)을 읽습니다.
- cursor의 정렬·쿼리를 바꾸면 [Persistence](persistence.md)를 읽습니다.
- API 계약의 검증 항목은 [Testing](testing.md#검증-대상별-증거)을 읽습니다.
