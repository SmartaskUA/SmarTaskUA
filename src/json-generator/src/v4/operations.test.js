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

describe('fixed days', () => {
  const fix = (state, ...days) => days.reduce((s, [eid, date, code]) => ops.setFixedDay(s, eid, date, code), state);
  const line = (e) => `${e.EmployeeCode} ${e.Date} ${e.ScheduleCode}`;

  it('writes no result until a day is fixed, and none with the menu off', () => {
    const s = sampleState();
    expect(buildBundle(s).result).toBeNull();
    const fixed = fix(s, ['EMP001', '2026-03-02', 9003]);
    expect(buildBundle(fixed).result.OutRosterTeamDays).toHaveLength(1);
    const off = buildBundle({ ...fixed, schedules: { ...fixed.schedules, enabled: false } });
    expect(off.result).toBeNull();
    expect(Object.keys(off.files)).not.toContain('result_schedules.csv');
  });

  it('writes the roster order then the date, and a sidecar of the codes used', () => {
    const s = fix(sampleState(),
      ['EMP002', '2026-03-03', 9003], ['EMP001', '2026-03-06', 3], ['EMP001', '2026-03-02', 9003], ['EMP003', '2026-03-03', 9001]);
    const { result, files } = buildBundle(s);
    expect(result.OutRosterTeamDays.map(line)).toEqual([
      'EMP001 2026-03-02T00:00:00 9003', 'EMP001 2026-03-06T00:00:00 3',
      'EMP002 2026-03-03T00:00:00 9003', 'EMP003 2026-03-03T00:00:00 9001'
    ]);
    expect(result.OutRosterTeamDays[0]).toEqual({
      RosterCode: 'SAMPLE', TeamCode: '1', EmployeeCode: 'EMP001', Date: '2026-03-02T00:00:00', ScheduleCode: 9003,
      OutRosterTeamDayTasks: [], OutRosterTeamDayResponsibilities: []
    });
    expect(files['result_schedules.csv']).toBe('code,description,scheduleWeightMinutes,startMin,endMin\n' +
      '3,Day off,0,,\n9001,09:00-13:00,240,540,780\n9003,09:00-17:00,480,540,1020\n');
    const { report } = ops.validateState(s);
    expect(messages(report.errors)).toEqual([]);
    expect(messages(report.warnings)).toEqual([]);
    expect(report.stats).toMatchObject({ rosterDays: 4, rosterDaysExpected: 28, rosterDaysLeft: 24, sidecarCodes: 3 });
    expect(ops.resultCounts(s)).toEqual({ entries: 4, fixed: 4, expected: 28, open: 24 });
  });

  it('changes a day, keeps one entry of a duplicated day, and opens it again', () => {
    let s = fix(sampleState(), ['EMP001', '2026-03-02', 9003]);
    s = ops.setFixedDay(s, 'EMP001', '2026-03-02', 9001);
    expect(s.result.entries.map(line)).toEqual(['EMP001 2026-03-02T00:00:00 9001']);

    s = { ...s, result: { ...s.result, entries: [...s.result.entries, { ...s.result.entries[0], ScheduleCode: 3 }] } };
    expect(messages(ops.validateState(s).report.errors)).toContain(
      'OutRosterTeamDays[1]: EMP001 already has an entry for 2026-03-02');
    expect(ops.fixedIndex(s).EMP001['2026-03-02'].ScheduleCode).toBe(9001);
    s = ops.setFixedDay(s, 'EMP001', '2026-03-02', 9003);
    expect(s.result.entries.map(line)).toEqual(['EMP001 2026-03-02T00:00:00 9003']);

    s = ops.setFixedDay(s, 'EMP001', '2026-03-02', null);
    expect(s.result.entries).toEqual([]);
  });

  it('holds each fixed day to its cell, in the validator\'s words', () => {
    const s = fix(sampleState(), ['EMP002', '2026-03-04', 9003], ['EMP002', '2026-03-02', 9001]);
    expect(messages(ops.validateState(s).report.errors)).toEqual([
      "OutRosterTeamDays[0]: ScheduleCode 9001 for EMP002 on 2026-03-02 contradicts the cell '8': " +
        'the shift is 240 min but the cell asks for 480',
      "OutRosterTeamDays[1]: ScheduleCode 9003 for EMP002 on 2026-03-04 contradicts the cell 'VAC': " +
        "the cell is 'VAC' (unavailable), but the day is worked"
    ]);
    const menu = ops.menuCatalogue(s);
    const problem = buildBundle(s).problem;
    expect(ops.analyseFixedDay(9001, { menu, cell: '8', problem, contractMinutes: 480 }).reason)
      .toBe('the shift is 240 min but the cell asks for 480');
    expect(ops.analyseFixedDay(3, { menu, cell: undefined, problem, contractMinutes: 480 }))
      .toMatchObject({ reason: '', unknown: false });
    expect(ops.analyseFixedDay(9003, { menu, cell: undefined, problem, contractMinutes: 480 }).reason)
      .toBe('the cell is blank (no assignments), but the day is worked');
    expect(ops.analyseFixedDay(7777, { menu, cell: 'A', problem, contractMinutes: 480 }).unknown).toBe(true);
  });

  it('follows renames and removals, and drops days outside the scope', () => {
    let s = fix(sampleState(), ['EMP001', '2026-03-02', 9003], ['EMP002', '2026-03-03', 9003], ['EMP003', '2026-03-03', 9001]);
    s = ops.renameEmployee(s, 'EMP001', 'E1');
    s = ops.removeEmployee(s, 'EMP002');
    s = ops.renameScheduleCode(s, 9003, 9100);
    expect(s.result.entries.map(line)).toEqual(['E1 2026-03-02T00:00:00 9100', 'EMP003 2026-03-03T00:00:00 9001']);
    expect(ops.fixedCodeUsage(s, 9100)).toBe(1);

    s = { ...s, temporalScope: { start: '2026-03-03', end: '2026-03-08' } };
    expect(ops.outsideScope(s).fixed).toBe(1);
    expect(ops.pruneOutsideScope(s).result.entries.map(line)).toEqual(['EMP003 2026-03-03T00:00:00 9001']);
  });
});

describe('what the SmarTask app would refuse', () => {
  const warningsOf = (state) => ops.validateState(state).report.warnings.filter((f) => /^(app|solver): /.test(f.message));

  it('says nothing about a problem the app takes and its solvers can cover', () => {
    expect(warningsOf(sampleState())).toEqual([]);
  });

  it('warns when the problemId cannot be uploaded', () => {
    const s = sampleState();
    s.metadata.problemId = 'E2E WIZARD';
    expect(warningsOf(s)).toEqual([{
      message: "app: metadata.problemId 'E2E WIZARD' cannot be uploaded to the SmarTask app, which takes letters, digits, "
        + "'_', '-' and '.', starting with a letter or digit, at most 64 characters",
      step: 'setup'
    }]);
    s.metadata.problemId = 'C2_January_2026';
    expect(warningsOf(s)).toEqual([]);
  });

  it('warns, with the solver\'s rule, when the menu leaves work days without a shift', () => {
    const s = sampleState();
    s.schedules = { ...s.schedules, rows: s.schedules.rows.filter((r) => r.startMin === null) };
    expect(warningsOf(s)).toEqual([{
      message: "solver: 20 work day(s) have no menu shift that fits their cell (e.g. EMP001 on 2026-03-02, cell 'A', "
        + "contract 480 min), so SmarTask's solvers would reject the package: add shifts in Shift Menu (Generate from "
        + 'contracts) or switch the menu off to let the solver build them',
      step: 'schedules'
    }]);
    // Without a menu the solver builds its own shifts.
    expect(warningsOf({ ...s, schedules: { ...s.schedules, enabled: false } })).toEqual([]);
  });

  it('counts only the days the missing length leaves uncovered', () => {
    const s = sampleState();
    s.schedules = { ...s.schedules, rows: s.schedules.rows.filter((r) => r.scheduleWeightMinutes !== 480) };
    const [warning] = warningsOf(s);
    expect(warning.message).toMatch(/^solver: \d+ work day\(s\) have no menu shift that fits their cell \(e\.g\. EMP001 on 2026-03-02/);
    expect(Number(warning.message.match(/\d+/)[0])).toBeLessThan(20);
  });
});
