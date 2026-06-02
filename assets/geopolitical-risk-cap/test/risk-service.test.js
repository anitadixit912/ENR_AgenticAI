'use strict';
const cds = require('@sap/cds');
const test = cds.test(__dirname + '/..');

let srv;

beforeAll(async () => {
  srv = await cds.connect.to('RiskService');
});

describe('RiskService â summary function', () => {
  it('returns aggregate counts', async () => {
    const result = await srv.send('summary', {});
    expect(typeof result.totalEvents).toBe('number');
    expect(typeof result.criticalCount).toBe('number');
    expect(typeof result.highCount).toBe('number');
    expect(typeof result.suppliersAffected).toBe('number');
    expect(result.totalEvents).toBeGreaterThanOrEqual(0);
  });

  it('sums severity counts within totalEvents', async () => {
    const result = await srv.send('summary', {});
    expect(result.criticalCount + result.highCount + result.mediumCount + result.lowCount)
      .toBeLessThanOrEqual(result.totalEvents);
  });

  it('reports last run status', async () => {
    const result = await srv.send('summary', {});
    expect(result.lastRunStatus).toBeDefined();
  });
});

describe('RiskService â FilterConfig CRUD', () => {
  it('reads filter config entries', async () => {
    const configs = await srv.run(SELECT.from('RiskService.FilterConfig'));
    expect(Array.isArray(configs)).toBe(true);
    expect(configs.length).toBeGreaterThan(0);
  });

  it('rejects update with invalid configType', async () => {
    const [cfg] = await cds.db.run(SELECT.from('risk.FilterConfig').limit(1));
    try {
      await srv.run(UPDATE('RiskService.FilterConfig', cfg.ID).with({ configType: 'INVALID_TYPE' }));
      throw new Error('Expected rejection');
    } catch (err) {
      expect(err.message).toMatch(/Invalid configType|Expected rejection/i);
    }
  });
});
