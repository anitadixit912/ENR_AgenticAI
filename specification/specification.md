# Specification

> **Guidelines**: Read [guidelines.md](./guidelines.md) before executing ANY tasks below.

Check off items as completed.

## Solution Setup

- [x] Create asset directories: `mkdir -p assets/geopolitical-risk-agent/ assets/geopolitical-risk-cap/`
- [x] Invoke `setup-solution` skill to create `solution.yaml` and `asset.yaml` files for every asset
- [x] Validate all `asset.yaml` and `solution.yaml` files exist and are well-formed

## Asset Implementation

- [x] Execute specification/geopolitical-risk-agent/specification.md (all items)
- [x] Execute specification/geopolitical-risk-cap/specification.md (all items)
- [x] Cross-implementation compatibility check:
  - [x] Verify agent `persist_risk_event` tool POSTs to the correct CAP endpoint (`/risk/RiskEvents`) — service is mounted at `/risk` via `@(path: '/risk')` annotation, NOT `/odata/v4/risk/RiskEvents`
  - [x] Verify CAP `RiskEvents` entity fields match the agent persist payload schema (field names, types)
  - [x] Verify CAP `FilterConfig` entity is readable by the agent to load monitored regions/themes at runtime
  - [x] Verify agent environment variable `CAP_SERVICE_URL` is documented and referenced consistently
  - [x] Verify both assets use the same severity enum values: Low / Medium / High / Critical
  - [x] Verify `recommendations` field exists in CAP `RiskEvents` entity (LargeString/CLOB) and agent serialises it as JSON string before POST
  - [x] Verify `send_alert_email` in agent receives `recommendations` list from `score_risk` output and renders numbered list in email body
  - [x] Verify Alert Detail page in React dashboard parses `recommendations` JSON field and renders colour-coded panel
