# Specification: geopolitical-risk-cap

> **Guidelines**: Read [guidelines.md](../guidelines.md) and [guidelines-cap.md](../guidelines-cap.md) before executing ANY tasks below. Follow all constraints described there throughout execution.

## Basic Setup

- [x] Read `product-requirements-document.md` and `intent.md` from the project root
- [x] Invoke the `cap-development` skill from `assets/geopolitical-risk-cap/` to set up the CAP project structure
- [x] Install dependencies (`npm install`), validate the project starts (`cds watch`) and responds at port 4004

## CDS Data Model

- [x] Define CDS entity `RiskEvents` in `db/schema.cds`:
  - Key fields: `ID` (UUID), `createdAt` (DateTime)
  - Event fields: `eventId` (String), `eventDate` (DateTime), `headline` (String(500)), `sourceUrl` (String(2000)), `region` (String), `country` (String)
  - Risk fields: `severity` (String enum: Low/Medium/High/Critical), `scoreNumeric` (Integer), `justification` (String(1000))
  - Impact fields: `affectedSupplierCount` (Integer), `affectedPoCount` (Integer), `totalPoValue` (Decimal), `currency` (String(3))
  - SAP fields: `sapTaskIds` (String), `agentRunId` (String)
  - Recommendations field: `recommendations` (LargeString) â JSON-serialised array of AI-generated mitigation action strings, stored as CLOB
- [x] Define CDS entity `AffectedSuppliers` in `db/schema.cds`:
  - Key: `ID` (UUID)
  - Fields: `riskEvent` (Association to RiskEvents), `supplierId` (String), `supplierName` (String), `country` (String), `city` (String), `poNumbers` (String), `poValue` (Decimal), `sapTaskId` (String), `riskScoreUpdated` (Boolean)
- [x] Define CDS entity `AlertHistory` in `db/schema.cds`:
  - Key: `ID` (UUID)
  - Fields: `riskEvent` (Association to RiskEvents), `alertType` (String enum: EMAIL/SAP_TASK), `recipient` (String), `sentAt` (DateTime), `status` (String enum: SENT/FAILED), `messageId` (String)
- [x] Define CDS entity `AgentRuns` in `db/schema.cds`:
  - Key: `ID` (UUID)
  - Fields: `runId` (String), `triggeredAt` (DateTime), `completedAt` (DateTime), `status` (String enum: RUNNING/COMPLETED/FAILED), `eventsProcessed` (Integer), `highCriticalCount` (Integer), `tasksCreated` (Integer), `suppliersUpdated` (Integer), `emailsSent` (Integer), `errorMessage` (String)
- [x] Define CDS entity `FilterConfig` in `db/schema.cds` for R9 (configurable filters):
  - Key: `ID` (UUID)
  - Fields: `configType` (String enum: REGION/THEME/THRESHOLD), `configKey` (String), `configValue` (String), `isActive` (Boolean), `updatedAt` (DateTime)
- [x] Run `cds compile db/` to validate models

## OData Service

- [x] Define `RiskService` in `srv/risk-service.cds`:
  - Expose `RiskEvents`, `AffectedSuppliers`, `AlertHistory`, `AgentRuns`, `FilterConfig` as OData entities
  - Add read-only projections where appropriate
  - Add `@readonly` annotation to `AgentRuns` and `AlertHistory` (system-managed)
  - Add `@insertonly` restriction on `RiskEvents` and `AffectedSuppliers` (written by agent only, not UI)
- [x] Run `cds compile srv/` to validate service definitions

## Custom Service Handlers

- [x] Implement `srv/risk-service.js` custom handler:
  - `RiskEvents` AFTER READ: compute `daysAgo` virtual field from `eventDate`
  - `RiskEvents` AFTER READ: add `affectedSupplierNames` virtual field by joining `AffectedSuppliers`
  - `FilterConfig` BEFORE UPDATE: validate `configType` is one of allowed enum values
  - `GET /risk/summary` action: return aggregate counts (total events by severity, active high+critical, last run timestamp)
- [x] Write tests for all custom handler logic (follow `cap-development` skill testing guidelines)

## Sample/Seed Data

- [x] Create `db/data/risk-RiskEvents.csv` with 5 sample risk events (2 Critical, 2 High, 1 Medium) across Middle East and Eastern Europe
- [x] Create `db/data/risk-AffectedSuppliers.csv` with 8 sample affected suppliers linked to the seed events
- [x] Create `db/data/risk-FilterConfig.csv` with default active configuration:
  - REGION: UA, RU, IL, IQ, SA, AE, IR, SY, YE, LY, NG, EG (active)
  - THEME: CONFLICT, MILITARY_ATTACK, PROTEST, SANCTION (active)
  - THRESHOLD: alert_severity=High (active)

## React Dashboard (UI)

- [x] Scaffold React frontend in `assets/geopolitical-risk-cap/ui/` using SAP UI5 Web Components
- [x] Implement **Dashboard Home** (`/`) page:
  - Summary cards: Total Active Alerts, Critical Count, High Count, Suppliers Affected, Last Agent Run timestamp
  - World map with risk-coloured regions (red=Critical, orange=High, yellow=Medium, grey=Low) using a lightweight map library (e.g. react-simple-maps)
  - Recent alerts table: columns = Date, Region, Headline, Severity (badge), Suppliers, POs, Status
- [x] Implement **Alert Detail** (`/alerts/:id`) page:
  - Event headline, date, source URL, region, country
  - AI justification text block
  - AI Recommendations panel (displayed between justification and suppliers table when recommendations are present):
    - Panel background colour matches severity (Critical=red-tinted, High=orange-tinted, Medium=yellow-tinted, Low=green-tinted)
    - Numbered ordered list of mitigation actions parsed from the `recommendations` JSON field
    - "Generated by AI Â· Review before acting" disclaimer badge
  - Affected suppliers table: Supplier ID, Name, Country, PO Numbers, PO Value, SAP Task ID, Risk Updated (checkmark)
  - Alert history timeline: EMAIL sent / SAP Task created with timestamps
- [x] Implement **Suppliers at Risk** (`/suppliers`) page:
  - Filterable table of all affected suppliers across all events
  - Columns: Supplier, Country, Active Events, Open PO Value, Current Risk Score, Last Updated
  - Filter by: severity, country, date range
- [x] Implement **Configuration** (`/config`) page (R9):
  - Editable list of active monitored regions (country codes)
  - Editable list of active conflict themes (CAMEO codes)
  - Severity threshold selector for alerts (Low/Medium/High/Critical)
  - Save button POSTs to `FilterConfig` OData entity
- [x] Implement **Agent Runs** (`/runs`) page:
  - Table of all agent runs: Run ID, Triggered At, Status, Events Processed, High/Critical Count, Tasks Created, Error
  - Status badges: RUNNING (blue), COMPLETED (green), FAILED (red)
- [x] Connect all pages to CAP OData service via `fetch` calls to `/odata/v4/risk/`
- [x] Implement auto-refresh every 60 seconds on Dashboard Home page

## Backend Functionality in UI

- [x] All 7 must-have requirements (R1âR7) from PRD have a corresponding UI representation in the dashboard
- [x] Risk severity colour coding consistent across all pages: Critical=red, High=orange, Medium=yellow, Low=green
- [x] Navigation sidebar with links to: Dashboard, Suppliers at Risk, Configuration, Agent Runs

## Validation

- [x] Run `cds compile srv/` â must complete without errors
- [x] Run `cds watch` and verify:
  - `GET /risk/RiskEvents` returns sample data (service path is `/risk` via `@(path: '/risk')` annotation)
  - `GET /risk/AffectedSuppliers` returns sample data
  - `GET /risk/FilterConfig` returns default configuration
  - `GET /risk/summary()` returns aggregate summary
  - `GET /risk/RiskEvents?$select=recommendations` confirms the `recommendations` field is present and populated for seeded events
- [x] Run frontend and verify dashboard home renders with map, summary cards, and alerts table
- [x] Write and run tests for all custom handler logic
