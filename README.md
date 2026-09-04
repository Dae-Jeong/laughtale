# Laughtale

<p align="center">
  <img src="assets/laughtale-logo.png" alt="Laughtale logo" width="220">
</p>

> 실무에서 시간과 조건 때문에 아쉽게 남은 제품 경험을, 내 관점과 기준으로 끝까지 만들어 보는 개인 제품 실험실.

Laughtale은 포트폴리오용 예제 모음이나 단일 서비스가 아닙니다. 여러 프로젝트를 진행하며
"이렇게 만들었으면 좋았을 텐데"라고 남았던 문제와 경험을, 제약 없이 직접 정의하고
구현하는 나만의 놀이터입니다.

## Perspective

실무의 제품은 일정, 우선순위, 기존 구조, 조직의 의사결정 안에서 완성됩니다. 그 과정에서
충분히 다듬지 못한 경험과 시도하지 못한 선택이 생깁니다.

Laughtale에서는 그 아쉬움을 출발점으로 삼습니다. 기능을 빨리 추가하는 것보다, 내가 실제로
쓰고 싶고 납득할 수 있는 제품 경험인지를 더 중요한 기준으로 둡니다.

기술은 그 자체를 전시하기 위해 도입하지 않습니다. 제품에 필요한 이유나 확인하고 싶은 질문이
생겼을 때 가장 작은 형태로 적용하고, 실제 동작과 측정 결과를 통해 다음 구조를 결정합니다.

## How it grows

- 하나의 큰 제품 기반을 만듭니다.
- 제품의 필요가 분명해질 때, 서비스와 기능을 원하는 방향으로 점진적으로 늘립니다.
- 처음부터 서비스 경계를 고정하지 않습니다. 경계는 실제 요구와 운영상의 필요가 생길 때 정합니다.
- 각 backend service는 독립적으로 실행하고 배포할 수 있는 하나의 프로젝트로 구성합니다.
- 서비스의 목적에 따라 FastAPI, Spring Boot를 비롯한 서로 다른 기술을 선택할 수 있습니다.
- 새로운 인프라는 제품의 동작, 안정성, 처리량 또는 비용에 미치는 영향을 확인하며 도입합니다.

## Expected architecture

현재 예상하는 전체 형태는 다음과 같습니다. 세부 구성과 서비스는 제품이 구체화되면서 결정합니다.

```text
user
  -> edge gateway
       ├── apps/web                 React frontend
       └── services/<service-name>  independent backend services
              └── data, search, messaging as needed

infra/k8s                            deployment and runtime foundation
```

저장소도 같은 경계를 따라 확장합니다.

```text
laughtale/
├── apps/
│   └── web/
├── services/
│   └── <service-name>/
├── infra/
│   └── k8s/
└── assets/
```

Gateway는 외부 traffic의 단일 진입점이 되고, React frontend와 각 backend service로 요청을
전달합니다. Kubernetes는 이 구성요소들을 배포하고 연결하는 기반이 됩니다.

## Reliability and capacity

제품이 성장하면 대용량 traffic과 장애 상황을 재현할 수 있는 test 환경을 점진적으로
구축합니다. 측정한 처리량과 명시적인 수요 가정을 이용해 필요한 resource를 산정하고, 이를
월간 infrastructure cost의 최소·기준·고성장 시나리오로 연결합니다.

## Status

현재는 초기 구상 단계이며 아직 실행 가능한 애플리케이션은 없습니다.

구현이 추가되면 이 문서에 필요한 환경, 실행 방법, 테스트 방법을 함께 기록합니다.

## Principle

> 구조는 제품을 돕기 위해 존재합니다. 아직 해결할 제품 문제가 없다면, 구조를 먼저 복잡하게 만들지 않습니다.
