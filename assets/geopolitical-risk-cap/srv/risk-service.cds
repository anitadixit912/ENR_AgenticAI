using { risk } from '../db/schema';

service RiskService @(path: '/risk') {

  entity RiskEvents        as projection on risk.RiskEvents;
  entity AffectedSuppliers as projection on risk.AffectedSuppliers;
  entity AlertHistory      as projection on risk.AlertHistory;
  entity AgentRuns         as projection on risk.AgentRuns;
  entity FilterConfig      as projection on risk.FilterConfig;

  @readonly
  function summary() returns {
    totalEvents      : Integer;
    criticalCount    : Integer;
    highCount        : Integer;
    mediumCount      : Integer;
    lowCount         : Integer;
    suppliersAffected: Integer;
    lastRunAt        : DateTime;
    lastRunStatus    : String;
  };
}
