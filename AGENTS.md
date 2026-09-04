# Laughtale Agent Entry

1. Follow the machine-wide rules in `/Users/marin/AGENTS.md` first.
2. Use [`README.md`](README.md) as the project context for product, architecture, and infrastructure work.
3. Future ideas in the context below are reference only. Do not scaffold or install them until the admin asks.
4. If work drifts from the stated purpose, give a brief reminder. The admin's explicit current decision takes precedence.
5. Before implementing a significant feature or architecture decision, follow [`.agents/skills/spec-driven-development/SKILL.md`](.agents/skills/spec-driven-development/SKILL.md). Respect that Skill's declared exceptions for trivial, self-contained changes.

## Context to remember

- Grow one product gradually; do not front-load infrastructure or empty services.
- Treat each backend service as an independent project that may use FastAPI, Spring Boot, or another suitable stack.
- Infrastructure learning interests include Kubernetes scaling, high-traffic reliability, database replication, Elasticsearch, and Kafka.
- Capacity planning should connect measured throughput and demand assumptions to monthly infrastructure cost scenarios.
- These interests are reference context, not current implementation requirements.
