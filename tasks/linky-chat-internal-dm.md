# Linky Chat Internal DM

Status: spec-review  
Phase: Phase 1 · 명세 초안  
Updated: 2026-09-07  
Approval: 방향만 승인되었으며 이 명세의 세부 계약과 구현은 아직 승인되지 않았습니다.

[Phase 0 작업 지도](../.ideas/linky-chat/work-map.md) ·
[정합성 후보](../.ideas/linky-chat/reliability.md) ·
[배포 후보](../.ideas/linky-chat/deployment.md) ·
[개발 기준 안내](../docs/README.md#작업별-읽기) ·
[문서 생명주기](../docs/README.md)

## 1차 애플리케이션 컨펌 요약

첫 결과물은 두 합성 사용자가 서로 다른 브라우저에서 텍스트 DM을 주고받는 로컬 앱입니다.
현재 요청은 1차 앱 구체화로 반영하며 상세 명세·구현 계획·DB 실행 승인으로 자동 간주하지 않습니다.

| 영역 | 이번 결과물 |
| --- | --- |
| 화면 | 합성 사용자 선택, DM 본문 목록, 입력·전송, pending/결과 확인 중/stored/오류 상태입니다. |
| API | HTTP 메시지 저장·history 조회, WebSocket 구독·변경 알림입니다. |
| 데이터 | 사용자·대화방·참여자·메시지 네 테이블 후보를 사용하며 멱등성·방별 seq를 검증합니다. |
| 복구 | 새로고침·재접속·ACK/알림 유실에서 같은 원본을 조회하고 중복을 방지합니다. |
| 계측 | 아래 기본 Metrics를 앱에서 수집·조회 가능하게 구현하고 정상·실패 입력으로 검증합니다. |
| 실행 | Next.js Node + FastAPI 단일 프로세스의 loopback 실행을 후보로 둡니다. PostgreSQL은 기존 인스턴스의 승인된 논리 DB만 사용합니다. |

화면은 읽음·상대방 전달 완료를 stored와 혼동하지 않습니다. 이 앱은 제품의 첫 흐름이며
운영 인증·전체 채팅 기능·대용량 운영 보장을 완성한 결과물이 아닙니다.
외부 연동, 수정·삭제 이력, 그룹·첨부·검색, Prometheus/Grafana 설치, K8s 배포·HPA·대용량 부하는 후속입니다.
자원 관측과 확장 후보는 [작업 지도](../.ideas/linky-chat/work-map.md)를 참고하되 해당 전체 범위를 이번 앱에 끌어오지 않습니다.

## Objective (목표)

Laughtale의 첫 제품 vertical slice로 합성 사용자 두 명이 서로 내부 DM 텍스트를 보내고,
저장 결과와 재접속 복구를 두 브라우저에서 확인할 수 있는 계약을 정합니다. 이번 Phase 1은
`internal-chat`이 필요로 하는 `chat-core`의 권한·저장·멱등성·대화 내 순서·cursor 경계만
명세하며, 애플리케이션 구현이나 인프라 변경을 시작하지 않습니다.

## 예상 결과

- 내부 DM의 사용자 흐름, 소유권, 데이터·HTTP·실시간 전달 경계가 검토 가능한 상태로 존재합니다.
- commit 이후 ACK, 동일 요청 key의 재시도와 충돌, ACK 유실, 재접속 cursor 복구의 판정 기준이 존재합니다.
- 동시 쓰기와 pagination 중에도 메시지가 중복되거나 영구 누락되지 않는 순서 계약이 존재합니다.
- 내부 메시지가 외부 플랫폼 발송 경로에 들어가지 않는 금지 경계와 검증 기준이 존재합니다.
- 구현 전에 승인이 필요한 핵심 결정이 세 개 이하로 분리되어 있습니다.

## 현재 상태와 가정

Source-backed: 저장소는 초기 구상 단계이며 실행 가능한 애플리케이션이 아직 없습니다.
[`k3s-bootstrap.md`](k3s-bootstrap.md)는 frontend를 Next.js App Router의 Node server mode로
실행하고 설치된 pnpm을 package manager로 사용하는 선택을 이미 확정했습니다. 이 선택과
Next.js app·package가 아직 생성·설치되지 않은 현재 상태를 구분합니다. FastAPI, PostgreSQL,
Python·DB toolchain은 아래의 승인 전 후보입니다.

Assumption: 대표 사용자 흐름은 `user_a`와 `user_b`라는 비식별 합성 사용자, 두 사용자가
멤버인 DM 한 개, 서로 저장소가 격리된 브라우저 context 두 개로 검증합니다. 실제 사용자,
기존 Linky 코드, 의료 데이터, 인증 정보는 사용하지 않습니다.

Assumption: 첫 slice는 단일 chat backend process와 하나의 권위 있는 PostgreSQL write
database를 사용합니다. 별도 backend 서비스, replica, Redis, Kafka, 검색 engine, Kubernetes
workload를 선행 조건으로 두지 않습니다.

## 범위

### 포함합니다

- 합성 사용자 두 명의 1:1 텍스트 DM 생성 fixture와 메시지 송수신 화면을 포함합니다.
- 현재 DM 멤버의 전송·조회 권한과 비회원·다른 주체 사칭의 거부를 포함합니다.
- HTTP 쓰기, commit 이후 저장 ACK, commit 이후 best-effort 실시간 알림을 포함합니다.
- 동일 `client_message_id`의 재시도, 다른 payload 충돌, ACK 유실 후 결과 복구를 포함합니다.
- 대화별 `seq`, 오름차순 pagination, snapshot 경계, 재접속 cursor 복구를 포함합니다.
- 작은 동시 실행과 실패 주입으로 정상·실패·경합 결과를 판정하는 검증을 포함합니다.
- 기본 HTTP·저장 결과·WebSocket·history 복구 지표의 정의, 내부 수집 endpoint, 계측 검증을 포함합니다.

### 포함하지 않습니다

- 외부 플랫폼 연결·수신·발신, 내부 대화의 외부 공유·중계, provider account를 포함하지 않습니다.
- 그룹 대화, 멤버 추가·탈퇴, 읽음 receipt, typing, presence, 수정·삭제, 첨부, 검색을 포함하지 않습니다.
- 전체 회원가입, SSO, 운영 인증, 실제 사용자 관리, 운영 배포를 포함하지 않습니다.
- Kafka, Redis, Elasticsearch, replica, shard, K8s 추가 설치나 설정을 포함하지 않습니다.
- DB 생성·migration 실행, 공유 PostgreSQL 변경, 외부 부하 발생을 포함하지 않습니다.
- 13억 사용자 규모의 처리량·정확성·가용성을 달성하거나 입증했다고 주장하지 않습니다.

## 기능 소유권

| 경계 | 이번 명세가 정하는 책임 | 이번 명세가 갖지 않는 책임 |
| --- | --- | --- |
| `chat-core` | 메시지 identity, 대화 범위 key, 저장 결과, 대화별 `seq`, idempotency, history cursor를 정합니다. | 외부 provider DTO·SDK·전송 상태를 알지 않습니다. |
| `internal-chat` | DM 멤버 권한, 전송·조회 use case, 내부 대화 UI와 실시간 구독을 정합니다. | 외부 발송 권한이나 account routing을 갖지 않습니다. |
| `chat-workspace` | 이번 slice에서는 내부 DM 화면의 최소 표현만 후보로 둡니다. | 외부 상담 통합 화면과 channel 구분은 후속 범위입니다. |
| `channel-sync` | 이번 slice에 source·dependency·runtime 경로를 만들지 않습니다. | 외부 계정·대화·메시지 동기화는 별도 승인 작업입니다. |

[`k3s-bootstrap.md`](k3s-bootstrap.md)는 K3s·Traefik 실행 경로의 기존 제안입니다.
2026-09-07 확인한 실제 환경은 Lima Kubernetes이며 기존 task의 클러스터 계획과 다릅니다.
이번 앱은 loopback 실행을 후보로 두며 cluster·Gateway·container 설정을 변경하지 않습니다.
`apps/web` 구현 전 두 task의 승인 상태와 파일 소유권을 맞추고 중복 app을 생성하지 않습니다.

## 최소 stack 후보

| 책임 | 최소 후보 | 현재 결정 상태 |
| --- | --- | --- |
| Web 실행 | Next.js App Router + Node server mode | 기존 K3s task의 확정 선택이며 app·package는 아직 설치 전입니다. |
| Web package manager | pnpm | 기존 K3s task의 확정 선택이며 host에는 설치되어 있지만 app manifest·script는 아직 없습니다. |
| Web 언어 | TypeScript | 이번 명세의 승인 전 후보입니다. |
| Chat API | FastAPI + typed Python | 제안이며 설치 전입니다. |
| 저장소 | PostgreSQL + 미정 driver·mapping 도구 | 제안이며 database·schema를 만들지 않았습니다. |
| 실시간 알림 | WebSocket notification + HTTP history 복구 | 제안이며 전달 보장의 기준은 DB history입니다. |
| 실험 identity | loopback 전용 합성 session | 아래 제약을 포함한 제안입니다. |
| 검증 | Python test runner + 실제 격리 PostgreSQL + browser E2E | 도구와 정확한 명령은 구현 계획 승인 후 확정합니다. |

Next.js App Router의 Node server mode와 pnpm은 재승인 대상이 아닙니다. 정확한 runtime version,
Python package manager, FastAPI, PostgreSQL 사용 여부와 driver·mapping·migration 도구,
test framework는 Phase 2 승인 전에 선택합니다. 후보를 적었다는 이유로 dependency를 설치하지 않습니다.

## 제안 source layout

아래 경로는 구현 후 사용할 예정 경로이며 현재 존재를 주장하지 않습니다. 책임이 실제로
분리될 때만 파일을 만들고, 한 함수로 충분한 책임에 빈 class나 wrapper를 추가하지 않습니다.

```text
apps/web/
  app/internal-chat/[conversationId]/page.tsx
  src/features/internal-chat/
    InternalDmView.tsx
    internalDmClient.ts
services/chat/
  src/
    chat_core/
      domain/message.py
      application/message_store.py
      persistence/postgres_message_store.py
    internal_chat/
      application/send_direct_message.py
      application/list_direct_messages.py
      api/http.py
      api/realtime.py
  tests/
    unit/
    integration/
tests/e2e/
  internal-dm.spec.ts
```

HTTP adapter는 요청 parsing·형식 검증·session context 전달·응답 변환만 담당합니다.
`internal-chat` use case는 권한과 저장 순서를 조정하고, PostgreSQL query·transaction은
`chat-core`의 persistence adapter가 담당합니다. ORM object나 HTTP object를 계층 사이에
전달하지 않습니다.

## 최소 사용자 흐름

```mermaid
flowchart TB
    A["브라우저 A<br/>user_a"] -->|"HTTP send · client_message_id"| API["internal-chat API"]
    API -->|"권한 확인 · 한 transaction"| DB["PostgreSQL<br/>message · idempotency · seq"]
    DB -->|"COMMIT 성공"| API
    API -->|"stored ACK"| A
    API -->|"commit 이후 notification"| B["브라우저 B<br/>user_b"]
    B -->|"재접속 · last contiguous cursor"| HISTORY["history API"]
    HISTORY --> DB
    EXTERNAL["외부 플랫폼<br/>이번 흐름과 연결되지 않음"]
```

실시간 notification은 새 이력이 있음을 빠르게 알리는 수단입니다. 메시지 원본과 복구 기준은
PostgreSQL history이며, notification 수신 자체를 영속 전달이나 읽음으로 해석하지 않습니다.

## Identity와 권한 계약

1. 대표 E2E는 `user_a`, `user_b` 두 합성 사용자와 독립 browser context 두 개를 사용합니다.
2. 실험 session 생성은 loopback interface에서만 노출하고 synthetic identity만 선택할 수 있습니다.
3. 실험 session은 실제 인증이 아닙니다. 같은 machine의 호출자는 다른 synthetic user를 선택해
   사칭할 수 있으므로 인증 강도나 production security를 검증했다는 근거로 사용하지 않습니다.
4. production mode에서는 실험 session route를 mount하지 않으며, 실험 identity 설정이 켜져 있으면
   애플리케이션 시작을 실패시킵니다. 외부 interface에 bind한 상태에서도 사용할 수 없습니다.
5. client request에는 `sender_id`를 받지 않습니다. sender는 server가 확인한 session actor로만 정합니다.
   `sender_id` 같은 미정의 identity field를 보내면 형식 오류로 거부합니다.
6. 전송과 조회는 현재 actor가 해당 DM의 멤버인지 use case에서 확인합니다. 비회원과 존재하지 않는
   conversation은 같은 공개 오류로 응답해 conversation 존재 여부를 노출하지 않습니다.
7. replay 결과를 조회할 때도 actor와 conversation scope를 다시 확인합니다. Idempotency는 권한 우회가 아닙니다.
8. 브라우저 수를 늘리지 않는 비회원 권한 검증은 API·application test의 별도 fixture principal로 수행합니다.

## 메시지 저장과 ACK 계약

### 쓰기 요청 후보

`POST /v1/internal-conversations/{conversation_id}/messages`

```json
{
  "client_message_id": "018f0b8e-0000-7000-8000-000000000001",
  "text": "테스트 메시지"
}
```

- `client_message_id`는 송신 browser가 한 번 정하고 결과를 확인할 때까지 같은 값을 유지합니다.
- `client_message_id`는 유효한 UUID 문자열이어야 하며 잘못된 형식은 `422`로 거부합니다.
- `text`는 server 기준 1자 이상 2,000 Unicode code point 이하를 후보로 둡니다. `text.strip()`이
  빈 값인 공백-only 입력은 `422`로 거부하되, 통과한 원문을 trim하거나 정규화하지 않고 저장합니다.
- Idempotency scope는 `(conversation_id, authenticated_sender_id, client_message_id)`입니다.
- payload fingerprint는 contract version과 검증된 `text`의 정확한 UTF-8 값을 포함합니다.
  공백이나 Unicode를 몰래 정규화해 같은 payload로 취급하지 않습니다.
- 신규 저장은 `201`, 같은 key·같은 payload의 replay는 `200`을 반환하는 후보로 둡니다.
  두 응답은 같은 `message_id`, `conversation_id`, `sender_id`, `client_message_id`, `seq`,
  `state: stored`를 반환합니다.
- 같은 key에 다른 payload가 오면 `409 idempotency_conflict`로 거부합니다. 기존 message를
  덮어쓰거나 새 message·새 `seq`를 만들지 않습니다.

### 한 대화의 쓰기 transaction

1. transaction을 시작하고 conversation row를 잠급니다.
2. 같은 transaction에서 DM membership과 idempotency key를 확인합니다.
3. 기존 key이면 payload fingerprint와 결과 조회 권한을 확인하고 새 쓰기 없이 기존 결과를 반환합니다.
4. 신규 key이면 transactional conversation counter를 `N`에서 `N+1`로 바꾸고 `seq=N+1`인
   message를 저장합니다.
5. `(conversation_id, seq)`와 idempotency scope에 database unique constraint를 둡니다.
6. counter·message·idempotency 결과를 모두 commit한 뒤에만 `stored` ACK를 만듭니다.
7. 실시간 notification은 commit 이후에 시도하며, 실패 때문에 저장된 message를 rollback하거나
   외부 발송으로 우회하지 않습니다.

DB commit이 실패하거나 rollback되면 저장 ACK를 반환하지 않습니다. HTTP connection이 commit
결과를 받기 전에 끊기면 client는 실패로 단정하거나 새 key를 만들지 않고 같은 key로 재시도합니다.

## 대화 내 순서와 cursor 계약

`seq`는 같은 conversation 안에서 commit되어 읽을 수 있는 저장 순서입니다. 사용자가 버튼을 누른
시각, client timestamp, server 접수 시각, 서로 다른 conversation의 전역 순서를 뜻하지 않습니다.

### `seq` 할당 불변조건

- conversation row의 counter 변경과 message insert를 같은 transaction에서 수행하고 row lock을
  commit 또는 rollback까지 유지합니다.
- 먼저 lock을 잡은 transaction이 끝나기 전에는 다음 writer가 `N+1`을 할당할 수 없습니다.
  rollback된 counter 변경도 함께 취소되므로 첫 slice의 committed `seq`는 1부터 연속입니다.
- PostgreSQL `sequence/nextval`처럼 rollback과 무관하게 번호를 소비하는 값을 cursor의 연속성
  근거로 사용하지 않습니다.
- transaction A가 작은 `seq`를 할당한 채 미commit이고 transaction B가 큰 `seq`를 먼저 commit하는
  구조를 허용하지 않습니다. 이 구조를 바꾸려면 별도의 commit visibility watermark와 gap 복구
  계약을 먼저 승인해야 합니다.
- client는 notification에서 큰 `seq`를 먼저 보더라도 gap을 건너뛰어 cursor를 전진하지 않습니다.
  cursor는 화면에 연속으로 반영한 마지막 `seq`만 나타냅니다.

이 불변조건 때문에 `seq` 할당 순서와 commit 순서가 어긋나 작은 `seq`가 늦게 보이는 동안
client가 큰 `seq`를 cursor로 저장해 작은 message를 영구 누락하는 경로를 차단합니다.

### Pagination 후보

첫 page는
`GET /v1/internal-conversations/{conversation_id}/messages?after_seq={cursor}&limit={limit}`로
요청합니다. 다음 page는 응답받은
`snapshot_head_seq`를 같은 query parameter로 함께 보냅니다.

1. `after_seq`와 `snapshot_head_seq`는 0 이상의 정수이며, `limit`은 생략하면 50, 허용 범위는
   1 이상 100 이하를 후보로 둡니다. 형식이나 범위를 벗어나면 `422`로 거부합니다.
2. 첫 page에서 server는 조회 시점의 committed conversation counter를 `snapshot_head_seq`로 고정합니다.
3. 모든 page에서 `0 <= after_seq <= snapshot_head_seq <= committed_head`를 검증합니다.
4. page query는 `seq > after_seq AND seq <= snapshot_head_seq ORDER BY seq ASC LIMIT limit`입니다.
5. 다음 page는 첫 응답의 같은 `snapshot_head_seq`를 query에 넣고 직전 page의 마지막 `seq`를
   `after_seq`로 사용합니다. 현재 committed head보다 큰 snapshot 값은 거부합니다.
6. `next_cursor`는 마지막으로 반환한 item의 `seq`입니다. 빈 page는 입력 `after_seq`를 그대로
   반환하며 page에 없는 server 최댓값으로 건너뛰지 않습니다.
7. 첫 slice에는 삭제가 없으므로 마지막 page까지 합친 `seq`는 `(initial_cursor, snapshot_head_seq]`
   구간과 정확히 일치해야 합니다. 중복·gap·역순이면 성공으로 처리하지 않습니다.
8. pagination 중 새로 commit한 `seq > snapshot_head_seq`는 현재 snapshot에 섞지 않고 실시간 buffer
   또는 다음 catch-up에서 처리합니다.
9. Client는 `last_contiguous_seq`, pagination snapshot, buffer를 `conversation_id`별로 분리합니다.
   한 conversation의 cursor 최댓값을 다른 conversation에 재사용하지 않습니다.

위 수치는 승인 전 후보입니다. 0건, 정확히 한 page, 한 page를 하나 넘는 경우, 여러 page와
동시 append 경계를 모두 검증합니다.

## ACK 유실과 재접속 복구

```mermaid
sequenceDiagram
    participant A as 브라우저 A · user_a
    participant API as internal-chat API
    participant DB as PostgreSQL
    participant B as 브라우저 B · user_b

    A->>API: key K로 message 전송
    API->>DB: BEGIN · conversation row lock
    API->>DB: membership · K 확인 · seq=42 저장
    API->>DB: COMMIT
    DB-->>API: message M · seq=42 저장 성공
    API--xA: stored ACK 유실
    API--xB: notification도 단절 중 유실 가능
    A->>API: 같은 key K · 같은 payload 재시도
    API->>DB: 권한과 기존 K 결과 조회
    DB-->>API: 기존 M · seq=42
    API-->>A: 200 · 기존 stored 결과
    B->>API: 구독 성립 · 들어오는 event buffer
    B->>API: after_seq=41로 history 요청
    API->>DB: snapshot_head_seq=42까지 오름차순 조회
    DB-->>API: M · seq=42
    API-->>B: M · next_cursor=42 · snapshot_head_seq=42
    Note over B: gap 없이 반영한 뒤 cursor를 42로 전진합니다.
```

재접속 client는 구독을 먼저 성립시키고 이후 notification을 제한된 buffer에 둔 다음 history를
동기화합니다. History와 buffer를 `(conversation_id, seq)`로 중복 제거하고 snapshot 이후 event를
이어 처리합니다. Buffer 한도를 넘거나 gap이 남으면 cursor를 임의로 올리지 않고 마지막 연속
cursor부터 동기화를 다시 시작합니다. 재접속과 앱 focus 시 server head를 즉시 다시 비교합니다.

연결과 focus가 계속 유지되어 gap을 알려 줄 다음 notification도 없는 경우를 위해, 승인 전 후보로
foreground의 현재 DM에서 5초마다 head 조회를 시도합니다. 이전 재조정이 진행 중이면 요청을
겹치지 않습니다. Head 비교도 현재 cursor로 같은 history endpoint를 호출해 응답의
`snapshot_head_seq`를 확인하며 별도 protocol을 추가하지 않습니다. 성공한 head가
`last_contiguous_seq`보다 크면 같은 history 계약으로 동기화합니다.
Foreground이고 network 요청이 성공할 수 있는 상태라면 마지막 notification 하나가 유실되어도
`주기 5초 + 성공한 head/history 조회와 render 지연` 안에 복구합니다. 실패한 조회는 cursor를
전진시키지 않고 다음 가능한 주기에 다시 시도합니다. Browser의 background timer 제한·suspend와
network 장애가 지속되는 동안에는 이 시간 범위를 보장하지 않으며, foreground 복귀·focus·재접속
trigger에서 즉시 재조정합니다.

## 외부 발송 차단 계약

- Internal DM write use case에는 external sender Port, provider account, channel mapping을 주입하지 않습니다.
- `conversation.kind=internal_direct` message는 외부 발송 대상 query·job·adapter의 입력이 될 수 없습니다.
- 실시간 notification 실패를 외부 API 호출로 보상하지 않습니다.
- 현재 source layout에는 `channel-sync` 구현을 만들지 않습니다.
- 후속 외부 연계가 추가될 때는 내부 conversation fixture가 외부 adapter 호출을 0회로 유지하는
  회귀 test를 반드시 포함하고, 같은 UI에 표시하더라도 send command를 공유하지 않습니다.

## 코드 스타일 실제 규칙의 작은 예

아래는 구현 코드가 아니라 승인 후 적용할 typed contract 예입니다. Python은 `snake_case`,
keyword-only input, 명시적 반환 type, 불변 data를 사용하고 client가 보낸 sender identity를 받지 않습니다.

```python
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class StoredMessage:
    message_id: UUID
    conversation_id: UUID
    sender_id: UUID
    client_message_id: UUID
    seq: int


async def send_direct_message(
    *,
    actor_id: UUID,
    conversation_id: UUID,
    client_message_id: UUID,
    text: str,
) -> StoredMessage:
    """인증된 actor를 sender로 사용해 내부 DM을 한 번만 저장합니다."""
    ...
```

- 이름은 `send_direct_message()`처럼 업무를 표현하며 `process()`·`handle()`을 새 업무 이름으로 쓰지 않습니다.
- Domain은 HTTP, ORM, framework object를 알지 않으며 exception은 복구·번역 책임이 있는 경계에서 처리합니다.
- 발생 시각은 timezone-aware UTC로 저장합니다. 대화 순서는 timestamp가 아니라 `seq`로 판정합니다.
- TypeScript는 strict type을 사용하고 API payload를 무검증 type assertion으로 신뢰하지 않습니다.
- 주석·docstring은 이름을 반복하지 않고 identity·순서처럼 숨은 업무 이유를 한국어로 설명합니다.

## Success Criteria

### 정상 경로

| ID | 재현 | 통과 기준 |
| --- | --- | --- |
| N1 | 독립 browser A/B를 각각 `user_a`/`user_b` synthetic session으로 열고 A가 DM을 보냅니다. | A는 commit된 `stored` ACK를 받고 B는 같은 `message_id`·`seq`의 text를 봅니다. DB 원본은 한 행입니다. |
| N2 | B가 답장하고 두 browser를 새로고침합니다. | 두 사용자가 권한 있는 같은 history를 `seq ASC`로 보며 sender와 text가 뒤바뀌지 않습니다. |
| N3 | 0건, 정확히 page 크기, page 크기+1, 여러 page의 history를 조회합니다. | 모든 item이 snapshot 범위에 한 번씩만 나타납니다. `next_cursor`는 마지막 item의 `seq`이고 빈 page에서는 입력 cursor 그대로입니다. |
| N4 | page 1 조회 뒤 새 message를 동시에 append합니다. | 기존 snapshot page에는 섞이지 않고 buffer 또는 다음 catch-up에서 한 번 나타납니다. |
| N5 | 유효 UUID, text 1자·2,000자, limit 생략·1·100 경계와 conversation 두 개의 cursor state를 확인합니다. | 유효 경계값은 계약대로 처리되고 기본 limit는 50입니다. 각 conversation의 cursor·snapshot·buffer는 서로 영향을 주지 않습니다. |

### 실패 경로

| ID | 재현 | 통과 기준 |
| --- | --- | --- |
| F1 | 비회원 fixture가 알려진 DM을 조회·전송하고 browser A가 `sender_id=user_b`를 주입합니다. | 자원 존재와 본문을 노출하지 않고 거부하며 message·counter가 변하지 않습니다. sender 주입은 형식 오류입니다. |
| F2 | message transaction을 commit 전에 실패·rollback시킵니다. | `stored` ACK와 notification이 없고 counter·message·idempotency 결과가 함께 남지 않습니다. 같은 key를 다시 보내면 한 번 저장할 수 있습니다. |
| F3 | commit 뒤 HTTP response를 유실하고 같은 key·같은 payload를 재시도합니다. | 기존 `message_id`와 `seq`를 반환하며 DB message는 한 행이고 새 notification 효과를 중복 생성하지 않습니다. |
| F4 | 같은 key에 다른 text를 보냅니다. | `409 idempotency_conflict`이며 기존 text·seq를 덮어쓰지 않고 새 message를 만들지 않습니다. |
| F5 | recipient notification을 유실한 뒤 `last_contiguous_seq`로 재접속합니다. | 현재 권한과 snapshot 범위의 누락 message를 history로 회복하고 gap을 건너뛰지 않습니다. |
| F6 | local 외의 interface 또는 production mode에서 실험 identity를 켭니다. | route를 사용할 수 없거나 시작이 실패하며 실험 session을 운영 인증으로 사용할 수 없습니다. |
| F7 | 내부 DM을 보낸 뒤 외부 발송 관련 대역의 호출을 확인합니다. | 외부 adapter·provider 호출은 0회이며 내부 message는 외부 queue·outbox에 나타나지 않습니다. |
| F8 | 잘못된 UUID, 공백-only·2,001자 text, limit 0·101, 음수·역전·현재 head 초과 cursor를 보냅니다. | `422`로 거부하며 message·counter·cursor state가 변하지 않습니다. |
| F9 | B의 연결과 focus를 유지한 채 마지막 notification 하나만 버리고 이후 notification을 만들지 않습니다. | Foreground와 정상 network에서 주기적 head/history 재조정으로 `5초 + 조회·render 지연` 안에 message를 복구하며 재접속·focus event에 의존하지 않습니다. |

### 경합 경로

| ID | 재현 | 통과 기준 |
| --- | --- | --- |
| C1 | 같은 sender가 같은 key·payload를 barrier로 100회 동시에 보냅니다. | 성공 효과는 message 1개와 `seq` 1개이며 모든 성공 응답은 같은 저장 결과를 가리킵니다. |
| C2 | 같은 key에 서로 다른 payload를 동시에 보냅니다. | 하나의 payload만 한 번 commit되고 나머지는 conflict입니다. 어느 payload가 이기는지 사전 보장하지 않습니다. |
| C3 | 같은 DM에 서로 다른 key를 여러 DB connection으로 동시에 보냅니다. | committed `seq`가 고유하고 1씩 증가하며 message가 덮어써지지 않습니다. |
| C4 | transaction A가 conversation row lock을 잡은 채 멈추고 transaction B가 다음 message를 보냅니다. | B는 A의 commit/rollback 전 다음 `seq`를 publish하지 못합니다. A rollback이면 번호를 소비하지 않고, commit이면 B가 그 다음 번호를 받습니다. |
| C5 | notification `seq=44`를 `seq=43`보다 먼저 client에 전달합니다. | client는 44를 buffer하고 cursor 42에서 history를 조회해 43을 채운 뒤 44까지 연속으로 전진합니다. |

## 테스트 전략

| 수준 | 검증 대상 | 필요한 증거 |
| --- | --- | --- |
| Domain/unit | message 값, payload fingerprint, cursor 연속성 규칙 | 외부 I/O 없이 같은 입력·충돌·gap 판정 결과를 확인합니다. |
| Application | session actor 사용, membership, 외부 발송 금지, ACK 생성 시점 | Port 대역으로 허용·거부, DB 변경 요청, external call 0회를 확인합니다. |
| Repository/integration | unique constraint, row lock, counter, commit·rollback, snapshot query | 실제 격리 PostgreSQL의 독립 connection과 barrier로 F2·C1–C4를 재현합니다. |
| HTTP contract | status, request/response field, 공개 오류, pagination | 신규·replay·conflict·권한 오류와 N3–N5, F8을 확인합니다. |
| Browser E2E | 두 synthetic session, 두 browser, 실시간 표시, ACK 유실·재접속·주기 복구 | 격리 browser context 두 개와 network/notification 실패 주입으로 N1–N2, F3, F5, F9를 확인합니다. |
| Negative control | 검사기가 실제 위반을 탐지하는지 확인 | 격리 test double에서 cursor를 큰 `seq`로 먼저 전진시키거나 idempotency 보호를 우회해 판정기가 실패하는지 확인합니다. |

테스트 database는 개발·운영 데이터와 격리하고 실행 전에 target을 확인합니다. 공유 PostgreSQL에
새 instance나 database를 이번 Phase에서 만들지 않습니다. 실제 test database 이름과 생성 방식은
Phase 2에서 별도 승인을 받아 정합니다. Test double 통과를 PostgreSQL 경합 통과로 대체하지 않습니다.

## 실행 명령 상태

### 첫 앱의 Metrics 계약 후보

[공통 Metrics](../external/backend-template/design/observability.md#metrics의-공통-판단-기준)와 [Runtime Review](../external/backend-template/design/runtime-review.md)를 따릅니다.
이 절은 채팅 고유 정의만 소유하며 도구 설치·공용 수집기·운영 설정을 확정하지 않습니다.

| 지표 | 목적·정의 | 검증 |
| --- | --- | --- |
| HTTP 요청 수·지연 | 저장과 history 경로를 template으로 구분합니다. 지연은 API 수신부터 응답 처리까지이며 브라우저 렌더링 시간이 아닙니다. | 알려진 정상·형식 오류·권한 오류 요청의 건수와 분류를 확인합니다. |
| 저장 결과 수 | 신규 commit·기존 결과 재확인·payload 충돌·실패·결과 불명을 구분합니다. DB 원장의 대체물은 아닙니다. | 신규 한 건 후 동일 키와 다른 payload를 재시도해 각 결과가 구분되는지 확인합니다. |
| 활성 WebSocket | 현재 프로세스의 연결 수이며 고유 사용자 수가 아닙니다. | 두 연결을 열고 종료해 gauge가 기준값으로 돌아오는지 확인합니다. |
| history 조회·복구 | 조회 시간·반환 건수를 기록합니다. 일반 조회를 전부 누락 복구로 집계하지 않습니다. 실제 gap 복구 판정은 클라이언트/E2E에서 확인합니다. | 알림 유실 뒤 조회로 원본을 복구하고 API 지표와 E2E 결과를 대조합니다. |
| 런타임·DB 진단 | 초기 프로세스 RSS·이벤트 루프 지연·DB 풀 대기·방 잠금 대기의 수집 가능성을 확인하고 구현 항목/미구현 항목을 구분합니다. | 수집된 값만 제시하며 측정 경로 미구현을 0이나 정상으로 표시하지 않습니다. |

이름·단위·histogram 경계와 구현 라이브러리는 계획 승인 전에 정합니다. 위의 요청·저장·연결·조회 계측은
첫 앱 완료 범위이며 런타임 심화 진단의 미구현 항목은 보고에 남깁니다. `/metrics`는 로컬 내부 수집용이며
외부 공개하지 않습니다. 수집기 설치 없이 endpoint 노출·값의 정확성까지 먼저 검증하고,
Prometheus/Grafana 대시보드와 HPA는 별도 작업으로 진행합니다.

### 앱 명령

현재 package manifest, source, test harness가 없으므로 실행 가능한 앱 명령은 아직 없습니다.
아래 항목은 구현 후 실제 구성에서 제공할 명령이며, 이 문서에서 가짜 command를 확정하지 않습니다.

| 목적 | 상태 |
| --- | --- |
| Web 개발·build·lint·type check | 구현 후 `apps/web`의 실제 package manager script로 제공합니다. |
| API 개발·lint·type check | 구현 후 `services/chat`의 실제 Python toolchain command로 제공합니다. |
| Unit·integration test | 격리 test database 계약과 함께 구현 후 제공합니다. |
| Browser E2E | 두 browser context와 실패 주입 fixture를 구현한 뒤 제공합니다. |

문서 작성 단계의 local link·구조 검사는 아래 검토 기록에 별도로 남깁니다. 문서 검사가
애플리케이션 build, test, browser 동작을 통과했다는 뜻은 아닙니다.

## 변경 경계

### Always

- 인증된 server session actor를 sender로 사용하고 DM membership을 use case에서 검사합니다.
- message·idempotency 결과·conversation counter를 한 transaction으로 commit한 뒤 ACK합니다.
- 동일 key replay와 다른 payload conflict를 DB constraint를 포함해 판정합니다.
- 공개 UUID·text·pagination 입력의 형식과 범위를 server에서 검증합니다.
- cursor를 conversation별 마지막 연속 `seq`로만 전진하고 pagination snapshot 경계를 유지합니다.
- Foreground에서는 5초 주기와 focus·재접속 trigger로 head/history를 재조정합니다.
- 내부 message를 외부 발송 경로와 source dependency에서 분리합니다.
- 실패·경합 test에서 응답뿐 아니라 DB 원본, counter, 호출 횟수를 함께 확인합니다.
- 합성 데이터만 사용하고 secret·session value·message 본문을 log에 남기지 않습니다.

### Ask

- 아래 세 핵심 미정 사항을 승인받고 나서 Phase 2 계획을 작성합니다.
- dependency 설치, source scaffold, database·schema·migration 생성 또는 변경 전에 확인합니다.
- ACK·idempotency scope·`seq`·cursor 불변조건을 바꾸거나 완화하기 전에 확인합니다.
- 운영 인증, 외부 플랫폼, broker·cache·replica·K8s를 범위에 추가하기 전에 확인합니다.

### Never

- 내부 message를 외부 provider, 외부 queue·outbox, channel routing으로 보내지 않습니다.
- client의 `sender_id`, timestamp, 표시명을 identity나 대화 순서의 근거로 신뢰하지 않습니다.
- DB commit 전에 `stored` ACK를 보내거나 notification 성공을 저장 성공으로 간주하지 않습니다.
- 큰 `seq`를 먼저 보았다는 이유로 gap을 건너뛰어 cursor를 전진하지 않습니다.
- rollback에서 번호를 소비하는 allocator를 연속 cursor 계약에 그대로 사용하지 않습니다.
- 실험 identity를 non-loopback·production에 노출하거나 실제 인증처럼 설명하지 않습니다.
- 실제 Linky code·의료 데이터·credential을 읽거나 복제하지 않습니다.
- 공유 PostgreSQL을 새로 띄우거나 변경하고, 외부 부하·운영 변경·commit·push를 수행하지 않습니다.

## 미정 사항 · 승인 필요

1. **Backend·저장소 stack과 위치:** `apps/web`은 기존 K3s task가 확정한 Next.js App Router
   Node server mode와 pnpm을 그대로 사용하며 재승인하지 않습니다. 새 `services/chat`에 FastAPI +
   PostgreSQL로 시작하는 안과 정확한 Python·DB driver·mapping·migration toolchain만 승인 후
   Phase 2에서 조사·고정합니다.
2. **실험 identity:** 두 browser 검증을 위해 loopback 전용 synthetic session을 추천합니다.
   이는 누구나 synthetic identity를 선택할 수 있는 spoofable harness이며, 실제 인증 검증과
   production 사용을 명시적으로 제외하는 조건으로 승인해야 합니다.
3. **저장·순서·복구 계약:** commit 후 stored ACK, 대화방 row-lock counter, 연속 `seq`,
   snapshot pagination, subscribe-before-catch-up과 foreground 5초 head 재조정을 한 묶음으로
   추천합니다. 처리량 최적화보다 영구 누락 방지를 우선하며, 이 계약을 완화하려면 대체
   watermark·gap 복구 증거가 필요합니다.

## Phase 1 검토 기록

| 검토 항목 | 결과 | 비고 |
| --- | --- | --- |
| 목표와 예상 결과 분리 | 통과 | 작업 objective와 검증 가능한 결과가 별도 section에 존재합니다. |
| 범위와 소유권 | 통과 | `chat-core`의 필요한 경계와 `internal-chat`만 명세하고 나머지는 제외합니다. |
| 정상·실패·경합 기준 | 통과 | N1–N5, F1–F9, C1–C5와 검증 수준의 대응을 대조했습니다. |
| Mermaid fence·구조 | 통과 | 최소 흐름과 ACK 유실·재접속 sequence의 fenced block 2개를 확인했습니다. |
| Mermaid 실제 렌더링 | 통과 | TB 변경 후 `/tmp/linky-chat-preview.zTM14C/verify-dm.cjs`를 다시 실행해 diagram 2개의 문법, 1440px overflow 없음, browser error 없음을 확인하고 두 이미지를 육안 확인했습니다. |
| Local Markdown link | 통과 | 이 문서와 `tasks/README.md`의 상대 link target이 checkout에 존재함을 확인했습니다. |
| Markdown LSP | 미지원 | 현재 `.md` LSP가 구성되지 않아 별도 diagnostic은 실행할 수 없습니다. |
| 앱 build·test·browser 검증 | 미실행 | 애플리케이션이 없고 구현 승인을 받지 않았습니다. |

## Human gate

이 문서는 Phase 1 검토 대상입니다. 관리자가 위 세 결정을 승인하거나 수정하기 전에는
Status를 바꾸지 않고 Phase 2 구현 계획, Phase 3 실행 checklist, source scaffold, dependency 설치,
database 작업을 작성하거나 수행하지 않습니다. `worker_done`이나 문서 검사 통과도 제품 인수,
세부 명세 승인, 구현 완료를 뜻하지 않습니다.
