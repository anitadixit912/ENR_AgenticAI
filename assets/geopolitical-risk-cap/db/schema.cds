using { cuid, managed } from '@sap/cds/common';

namespace risk;

entity RiskEvents : cuid, managed {
  eventId              : String(100);
  eventDate            : DateTime;
  headline             : String(500);
  sourceUrl            : String(2000);
  region               : String(10);
  country              : String(10);
  severity             : String(10) @assert.range enum { Low; Medium; High; Critical; };
  scoreNumeric         : Integer;
  justification        : String(1000);
  recommendations      : LargeString;
  affectedSupplierCount: Integer default 0;
  affectedPoCount      : Integer default 0;
  totalPoValue         : Decimal(15,2) default 0;
  currency             : String(3) default 'USD';
  sapTaskIds           : String(500);
  agentRunId           : String(100);
  suppliers            : Composition of many AffectedSuppliers on suppliers.riskEvent = $self;
  alerts               : Composition of many AlertHistory on alerts.riskEvent = $self;
}

entity AffectedSuppliers : cuid {
  riskEvent        : Association to RiskEvents;
  supplierId       : String(20);
  supplierName     : String(200);
  country          : String(10);
  city             : String(100);
  poNumbers        : String(500);
  poValue          : Decimal(15,2) default 0;
  sapTaskId        : String(100);
  riskScoreUpdated : Boolean default false;
}

entity AlertHistory : cuid, managed {
  riskEvent  : Association to RiskEvents;
  alertType  : String(20) @assert.range enum { EMAIL; SAP_TASK; };
  recipient  : String(200);
  sentAt     : DateTime;
  status     : String(10) @assert.range enum { SENT; FAILED; };
  messageId  : String(200);
}

entity AgentRuns : cuid, managed {
  runId            : String(100);
  triggeredAt      : DateTime;
  completedAt      : DateTime;
  status           : String(20) @assert.range enum { RUNNING; COMPLETED; FAILED; };
  eventsProcessed  : Integer default 0;
  highCriticalCount: Integer default 0;
  tasksCreated     : Integer default 0;
  suppliersUpdated : Integer default 0;
  emailsSent       : Integer default 0;
  errorMessage     : String(1000);
}

entity FilterConfig : cuid, managed {
  configType  : String(20) @assert.range enum { REGION; THEME; THRESHOLD; };
  configKey   : String(100);
  configValue : String(500);
  isActive    : Boolean default true;
}
