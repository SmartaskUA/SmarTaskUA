// @vitest-environment node
import { describe, it, expect } from 'vitest';
import * as ops from './operations';
import { buildBundle } from './generate';
import { sampleState } from './fixtures/sampleState';
import { schemaFindings } from './schema';

const messages = (findings) => findings.map((f) => f.message);

describe('a problem authored in the wizard', () => {
  it('validates with no errors and no warnings', () => {
    const { report } = ops.validateState(sampleState());
    expect(messages(report.errors)).toEqual([]);
    expect(messages(report.warnings)).toEqual([]);
    expect(report.stats).toMatchObject({ days: 7, openDays: 7, 'demandRows.periods': 19 });
  });

  it('passes the JSON Schema', () => {
    expect(schemaFindings(buildBundle(sampleState()).problem)).toEqual([]);
  });

  it('writes LF-only CSVs with the v4 headers, and no v2.6 keys', () => {
    const { problem, files } = buildBundle(sampleState());
    for (const text of Object.values(files)) expect(text).not.toMatch(/\r/);
    expect(files['periods_demand.csv'].split('\n')[0]).toBe('date,tableName,tableValue,minimum,ideal,estimated,start,end');
    expect(files['shifts_demand.csv']).toBe('date,workPeriod,tableName,tableValue,minimum,ideal,estimated,start,end\n');
    for (const key of ['features', 'optimization', 'operatingHours']) expect(problem).not.toHaveProperty(key);
    expect(problem.scheduleInput).toEqual({ dataFile: 'schedule_input.csv', dayOffCodes: expect.any(Object) });
  });
});

describe('the weekly template', () => {
  it('orders rows by dimension declaration, then start', () => {
    const rows = sampleState().demand.periods.filter((r) => r.date === '2026-03-02');
    expect(rows.map((r) => `${r.tableName}/${r.tableValue} ${r.start}`)).toEqual([
      'Team/T1 09:00', 'Team/T1 13:00', 'Responsibility/A 09:00'
    ]);
  });

  it('can leave holidays for manual editing, or fill only empty dates', () => {
    const s = sampleState();
    const skipped = ops.applyTemplate(s, { holidays: 'skip' });
    expect(skipped.demand.periods.some((r) => r.date === '2026-03-05')).toBe(false);
    const filled = ops.applyTemplate(skipped, { mode: 'fill' });
    expect(filled.demand.periods.filter((r) => r.date === '2026-03-05')).toHaveLength(3);
    expect(filled.demand.periods).toHaveLength(19);
  });

  it('finds overlapping windows for one dimension only', () => {
    const rows = [
      { date: 'd', tableName: 'Team', tableValue: 'T1', start: '09:00', end: '13:00' },
      { date: 'd', tableName: 'Team', tableValue: 'T1', start: '12:00', end: '14:00' },
      { date: 'd', tableName: 'Responsibility', tableValue: 'A', start: '09:00', end: '17:00' },
      { date: 'd', tableName: 'Team', tableValue: 'T1', start: '14:00', end: '15:00' }
    ];
    expect(ops.overlappingRows(rows)).toHaveLength(1);
  });
});

describe('cascades', () => {
  it('removes a dimension everywhere it is referenced, re-ranking priority', () => {
    const s = ops.removeDimension(sampleState(), 'Team', 'T1');
    expect(ops.dimensionUsage(s, 'Team', 'T1')).toEqual({ periods: 0, days: 0, shifts: 0, blocks: 0, competencies: 0, priority: 0 });
    expect(s.priorityHierarchy.map((e) => e.rank)).toEqual([1]);
  });

  it('renames a dimension everywhere it is referenced', () => {
    const s = ops.updateDimension(sampleState(), { tableName: 'Team', tableValue: 'T1' },
      { tableName: 'Team', tableValue: 'T9', name: 'Team 9' });
    expect(ops.dimensionUsage(s, 'Team', 'T1').periods).toBe(0);
    expect(ops.dimensionUsage(s, 'Team', 'T9')).toMatchObject({ periods: 12, competencies: 4, priority: 1 });
    expect(messages(ops.validateState(s).report.errors)).toEqual([]);
  });

  it('renames and removes day-off codes with their cells', () => {
    let s = ops.renameDayOffCode(sampleState(), 'DO', 'FOLGA');
    expect(Object.keys(s.scheduleInput.dayOffCodes)).toEqual(['FOLGA', 'VAC', 'NOT']);
    expect(ops.codeUsage(s, 'FOLGA')).toBe(5);
    s = ops.removeDayOffCode(s, 'FOLGA');
    expect(ops.codeUsage(s, 'FOLGA')).toBe(0);
    expect(s.scheduleInput.dataMatrix.EMP001['2026-03-06']).toBe('');
  });

  it('renames a contract in every assignment', () => {
    const s = ops.renameContract(sampleState(), 'FT_8h', 'FT_40');
    expect(ops.contractUsage(s, 'FT_40')).toBe(2);
    expect(ops.contractUsage(s, 'FT_8h')).toBe(0);
  });

  it('carries an employee\'s matrix row across a rename and drops it on removal', () => {
    let s = ops.renameEmployee(sampleState(), 'EMP001', 'E1');
    expect(s.scheduleInput.dataMatrix.E1['2026-03-06']).toBe('DO');
    s = ops.removeEmployee(s, 'EMP002');
    expect(s.scheduleInput.dataMatrix).not.toHaveProperty('EMP002');
  });
});

describe('the matrix', () => {
  it('fills uncovered days blank and covered days with A, keeping existing cells', () => {
    let s = sampleState();
    s.employees.list[0].contractAssignments = [{ contractType: 'FT_8h', start: '2026-03-04', end: null }];
    s.scheduleInput.dataMatrix = { EMP001: { '2026-03-06': 'DO' } };
    s = ops.fillMatrix(s);
    const row = s.scheduleInput.dataMatrix.EMP001;
    expect(row['2026-03-02']).toBe('');
    expect(row['2026-03-04']).toBe('A');
    expect(row['2026-03-06']).toBe('DO');
  });

  it('counts the weekly load the structural pass checks', () => {
    const { cap, byEmployee } = ops.weeklyLoad(sampleState());
    expect(cap).toBe(6);
    expect(byEmployee.EMP001).toEqual([{ week: 0, dates: expect.any(Array), nWk: 5 }]);
    expect(byEmployee.EMP002[0].nWk).toBe(5);
  });
});

describe('the menu generator', () => {
  it('covers every contract length inside the demand envelope, once', () => {
    const s = sampleState();
    const lengths = s.schedules.rows.filter((r) => r.startMin !== null).map((r) => r.scheduleWeightMinutes);
    expect(new Set(lengths)).toEqual(new Set([240, 480]));
    expect(ops.generateMenuRows(s, { stride: 240 })).toEqual([]);
    expect(s.schedules.rows[3]).toEqual({ code: 9001, description: '09:00-13:00', scheduleWeightMinutes: 240, startMin: 540, endMin: 780 });
  });
});
