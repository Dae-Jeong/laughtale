# Laughtale 프로젝트 방향

이 문서는 Laughtale이 무엇을 지향하는지 오래 유지하기 위한 기준이다. 저장소가 커지더라도
제품과 인프라 작업이 처음의 목적에서 벗어나지 않았는지 확인하기 위해 사용한다.

## 목적

Laughtale은 개인 제품 실험실이다. 실무의 시간과 조건 안에서 아쉽게 남았던 제품 경험을
다시 꺼내, 내가 납득할 수 있는 수준까지 내 관점으로 만들어 보는 공간이다.

기능만 구현하는 저장소는 아니다. 실제로 성장하는 하나의 제품을 배경으로, 아직 경험하지
못한 backend, infrastructure, reliability, data, operations 영역을 직접 적용하고 배운다.

## 결정 상태

- **확정:** 현재의 프로젝트 원칙이다. 작업은 특별한 이유가 없다면 이를 지킨다.
- **계획:** 제품에 필요가 생길 때 점진적으로 도입할 방향이다.
- **탐색:** 명시적인 실험을 통해 판단할 후보이며, 아직 아키텍처의 일부가 아니다.

## 확정한 원칙

### 제품이 구조보다 먼저다

- 개선하고 싶은 제품 문제나 경험에서 출발한다.
- 아키텍처와 인프라는 제품과 학습 목표를 지원하기 위해 존재한다.
- 시스템을 복잡해 보이게 만들기 위해 빈 서비스나 기술을 미리 추가하지 않는다.

### 하나의 성장하는 제품을 만든다

- Laughtale은 관계없는 예제의 모음이 아니라 하나의 큰 제품이다.
- 제품을 중심으로 기능과 서비스를 점진적으로 늘린다.
- 서비스 경계는 실제 소유권, 확장, 데이터, 운영상의 필요에서 정한다.

### Backend service는 독립된 프로젝트다

- `services/` 아래의 각 디렉터리는 독립적으로 실행하고 배포할 수 있는 backend 프로젝트다.
- 서비스마다 FastAPI, Spring Boot 또는 다른 적합한 기술을 의도적으로 선택할 수 있다.
- 모든 backend가 같은 언어나 공통 framework를 사용할 필요는 없다.
- 각 서비스는 구현, dependency, test, container image, data migration, API contract를 소유한다.

### 하네스보다 참고 기준을 우선한다

- 프로젝트 규약과 실험 기록은 작업을 안내하되, 그 자체가 거대한 framework가 되지 않게 한다.
- 자동화는 반복 작업이나 재현성의 필요가 확인된 뒤 도입한다.
- 문서에서는 확인된 사실, 가정, 향후 계획을 구분한다.

## 계획한 방향

다음은 앞으로 만들고 싶은 역량이며, 초기 세팅 요구사항은 아니다.

- 제품의 주 사용자 접점이 되는 React frontend
- 제품과 서비스가 성장할 수 있는 Kubernetes 기반
- frontend와 API traffic을 전달하는 하나의 외부 gateway. 구체적인 구현은 아직 정하지 않는다.
- 대용량 traffic에서 안정성을 검증할 수 있는 재현 가능한 load·resilience test 환경
- 명시적인 수요 가정과 측정한 service 처리량을 이용한 capacity planning
- 최소·기준·고성장 시나리오별 월간 infrastructure cost 예측
- latency, error, saturation, cost의 원인을 설명할 수 있는 observability

## 탐색할 영역

다음 기술은 제품 문제나 명확한 학습 실험이 근거가 될 때 하나씩 도입한다.

- Database primary/replica 구성, replication lag, failover, read routing
- Elasticsearch 등의 검색 엔진과 indexing·consistency 동작
- Kafka 등의 event platform과 delivery·ordering·retry·idempotency 동작
- Workload와 cluster node의 horizontal·vertical scaling
- Failure injection, overload 대응, graceful degradation
- Data 증가, storage, backup, recovery, network cost

## 현재의 아키텍처 형태

현재 합의한 개념적인 형태는 다음과 같다.

```text
user
  -> edge gateway
       -> apps/web
       -> services/<independent-backend>

infra/k8s
  -> gateway, web, services와 이후의 platform component를 배포하고 연결
```

구체적인 디렉터리 구조, gateway controller, backend 기술, data ownership, 배포 도구는 첫 번째
제품 흐름이 정해질 때 선택한다.

## API contract와 문서

- API contract는 서비스가 약속하는 기계 판독 가능한 interface이며, 대표적인 형식은 OpenAPI다.
- Swagger UI는 contract를 보여주고 시험할 수 있는 도구 중 하나다.
- 초기에는 각 service가 자신의 API contract를 가까이 두고 직접 소유한다.
- `docs/`에는 프로젝트 방향, 결정, 규약, 실험, 운영 지식을 기록한다.
- 중앙 contract catalog는 여러 consumer로 인해 실제 필요가 생길 때 추가한다.

## Capacity와 cost를 판단하는 방식

알 수 없는 미래 traffic은 정확한 척하는 단일 숫자나 추정 거부 대신, 명시적인 시나리오로
다룬다.

```text
demand 가정
  -> 평균·peak traffic 예측
  -> 측정한 service instance별 안전 처리량
  -> 필요한 replica, node, data infrastructure
  -> provider별 월간 비용
  -> 실제 사용량·비용과 비교하여 보정
```

모든 추정에는 가정, 신뢰 수준, 주요 비용 변수, 안전 여유, 재계산 조건을 함께 기록한다.

## 리마인드 체크리스트

Service, platform component, infrastructure dependency를 도입하기 전에 확인한다.

1. 어떤 제품 문제나 학습 질문을 해결하는가?
2. 지금 **확정**, **계획**, **탐색** 중 어디에 해당하는가?
3. 질문에 답할 수 있는 가장 작은 구성은 무엇인가?
4. 어떤 제품 동작, reliability, capacity, cost를 측정할 것인가?
5. 지속적으로 발생하는 복잡성과 비용은 무엇인가?
6. 관계없는 작업을 손상하지 않고 제거하거나 교체할 수 있는가?

작업이 이 질문을 건너뛸 때는 관련 원칙과 tradeoff를 짧게 리마인드한다. 답이 이미 분명한
상황에서는 체크리스트를 불필요한 절차로 만들지 않는다.
