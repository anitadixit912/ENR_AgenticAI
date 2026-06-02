const cds = require('@sap/cds');

module.exports = class RiskService extends cds.ApplicationService {
  async init() {

    const { RiskEvents, AffectedSuppliers, AgentRuns } = this.entities;

    // summary() function â aggregate counts
    this.on('summary', async () => {
      const db = await cds.connect.to('db');
      const events = await db.run(SELECT.from('risk.RiskEvents').columns(
        'severity', 'affectedSupplierCount', 'createdAt', 'agentRunId'
      ));
      const runs = await db.run(
        SELECT.one.from('risk.AgentRuns').orderBy({ createdAt: 'desc' })
      );

      const totalEvents = events.length;
      const criticalCount = events.filter(e => e.severity === 'Critical').length;
      const highCount = events.filter(e => e.severity === 'High').length;
      const mediumCount = events.filter(e => e.severity === 'Medium').length;
      const lowCount = events.filter(e => e.severity === 'Low').length;
      const suppliersAffected = events.reduce((sum, e) => sum + (e.affectedSupplierCount || 0), 0);

      return {
        totalEvents,
        criticalCount,
        highCount,
        mediumCount,
        lowCount,
        suppliersAffected,
        lastRunAt: runs ? runs.createdAt : null,
        lastRunStatus: runs ? runs.status : 'NO_RUNS'
      };
    });

    // Validate FilterConfig on update
    this.before('UPDATE', 'FilterConfig', req => {
      const { configType } = req.data;
      const allowed = ['REGION', 'THEME', 'THRESHOLD'];
      if (configType && !allowed.includes(configType)) {
        req.reject(400, `Invalid configType '${configType}'. Allowed: ${allowed.join(', ')}`);
      }
    });

    await super.init();
  }
};
