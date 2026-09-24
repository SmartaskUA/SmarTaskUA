// @vitest-environment node
/**
 * The domain layer, ported case for case from
 * json_generation/schema_v4/tests/test_core.py so the two cannot drift apart.
 */
import { describe, it, expect } from 'vitest';
import * as core from './core';
import { OPERATORS } from './constants';

const DAY_OFF = {
  scheduleInput: { dayOffCodes: { DO: { kind: 'preferable' }, VAC: { kind: 'unavailable' } } }
};
const iv = core.interval;

describe('numbers', () => {
  it.each([
    ['8', 8], ['7.2', 7.2], ['7,2', 7.2], ['  7,2  ', 7.2],
    ['', null], ['abc', null], [null, null]
  ])('tryNumber(%j) is %j', (text, expected) => {
    expect(core.tryNumber(text)).toBe(expected);
  });

  it('reads a lone comma as a decimal point, never a thousands separator', () => {
    expect(core.tryNumber('1,234')).toBe(1.234);
  });

  it('number throws where tryNumber returns null', () => {
    expect(() => core.number('abc')).toThrow(core.DomainError);
  });

  it.each([[8, '8'], [7.2, '7.2'], [432.0, '432'], [4.5, '4.5']])(
    'formatNumber(%j) is %j', (value, text) => {
      expect(core.formatNumber(value)).toBe(text);
    }
  );
});

describe('time', () => {
  it.each([
    ['09:00', '17:00', [540, 1020]],
    ['22:00', '06:00', [1320, 1800]],   // crosses midnight, resolved not inferred
    ['00:00', '00:00', [0, 1440]]       // a whole day, not an empty one
  ])('parseRange(%s, %s)', (start, end, expected) => {
    expect(core.tryParseRange(start, end)).toEqual(expected);
  });

  it('rejects a malformed boundary', () => {
    expect(core.tryParseRange('9am', '17:00')).toBeNull();
    expect(() => core.parseRange('9am', '17:00')).toThrow(core.DomainError);
  });

  it.each([[540, '09:00'], [1800, '06:00'], [1440, '00:00']])(
    'minToHhmm(%i) wraps past midnight', (minutes, text) => {
      expect(core.minToHhmm(minutes)).toBe(text);
    }
  );

  it('coalesces overlapping and touching intervals', () => {
    expect(core.coalesce([iv(480, 720), iv(600, 840)])).toEqual([iv(480, 840)]);
    expect(core.coalesce([iv(480, 720), iv(720, 960)])).toEqual([iv(480, 960)]);
    expect(core.coalesce([iv(450, 840), iv(1095, 1275)])).toHaveLength(2);
    expect(core.coalesce([])).toEqual([]);
  });

  it('treats overlap as half-open', () => {
    expect(core.overlaps(iv(1200, 1260), iv(1260, 1320))).toBe(false);
    expect(core.overlaps(iv(1200, 1260), iv(1230, 1320))).toBe(true);
  });

  it('converts a fractional contract exactly', () => {
    expect(core.hoursToMinutes(7.2)).toBe(432);
    expect(core.hoursToMinutes(8)).toBe(480);
    expect(core.hoursToMinutes(0.001)).toBeNull();
  });

  it('checks the grid', () => {
    expect(core.onGrid(480, 30)).toBe(true);
    expect(core.onGrid(432, 30)).toBe(false);   // Cenario 1's NL_36
    expect(core.onGrid(432, 24)).toBe(true);
  });
});

describe('the cell grammar', () => {
  it('reads a plain A as the contract length', () => {
    expect(core.classifyCell('A', DAY_OFF).kind).toBe('auto');
    expect(core.classifyCell('a', DAY_OFF).kind).toBe('auto');
  });

  it.each([['8', 480], ['7.2', 432], ['4', 240], ['7,2', 432]])(
    'reads numeric cell %s as hours', (hours, minutes) => {
      expect(core.classifyCell(hours, DAY_OFF).minutes).toBe(minutes);
    }
  );

  it('inverts the v3 minutes guard', () => {
    expect(() => core.classifyCell('480', DAY_OFF)).toThrow(/never converted/);
  });

  it.each(['0', '-3'])('refuses a working day of no hours (%s)', (cell) => {
    expect(() => core.classifyCell(cell, DAY_OFF)).toThrow(core.DomainError);
  });

  it('words the refusal the way Python does', () => {
    expect(() => core.classifyCell('0', DAY_OFF)).toThrow("cell '0': a working day of 0.0 hours");
  });

  it('refuses hours that are not whole minutes', () => {
    expect(() => core.classifyCell('7.001', DAY_OFF)).toThrow(/whole number of minutes/);
  });

  it.each(OPERATORS)('parses %s', (op) => {
    const rule = core.classifyCell(`${op}:09:00-13:00`, DAY_OFF);
    expect(rule.kind).toBe(op.toLowerCase());
    expect(rule.windows).toEqual([iv(540, 780)]);
  });

  it.each(OPERATORS)('parses %s case-insensitively', (op) => {
    expect(core.classifyCell(`${op.toLowerCase()}:09:00-13:00`, DAY_OFF).kind).toBe(op.toLowerCase());
  });

  it('coalesces multiple windows', () => {
    expect(core.classifyCell('EQUALS:08:00-12:00,10:00-14:00', DAY_OFF).windows).toEqual([iv(480, 840)]);
  });

  it('keeps a real gap as two windows', () => {
    expect(core.classifyCell('EQUALS:07:30-14:00,18:15-21:15', DAY_OFF).windows).toHaveLength(2);
  });

  it('lets an operator window cross midnight', () => {
    expect(core.classifyCell('WITHIN:22:00-06:00', DAY_OFF).windows).toEqual([iv(1320, 1800)]);
  });

  it.each(['EQUALS:nonsense', 'EQUALS:09:00', 'EQUALS:25:00-26:00'])('refuses %s', (cell) => {
    expect(() => core.classifyCell(cell, DAY_OFF)).toThrow(core.DomainError);
  });

  it('classifies declared codes and refuses undeclared ones', () => {
    expect(core.classifyCell('DO', DAY_OFF).dayOff).toBe('preferable');
    expect(core.classifyCell('VAC', DAY_OFF).dayOff).toBe('unavailable');
    expect(() => core.classifyCell('FDO', DAY_OFF)).toThrow(/not declared in scheduleInput.dayOffCodes/);
  });

  it('accepts a non-ASCII day-off code', () => {
    const problem = { scheduleInput: { dayOffCodes: { 'Fér': { kind: 'unavailable' } } } };
    expect(core.classifyCell('Fér', problem).dayOff).toBe('unavailable');
  });

  it('reads a blank cell as empty, not unconstrained', () => {
    expect(core.classifyCell('', DAY_OFF).kind).toBe('empty');
  });

  it('tryClassifyCell reports instead of throwing', () => {
    expect(core.tryClassifyCell('480', DAY_OFF).error).toMatch(/never converted/);
    expect(core.tryClassifyCell('8', DAY_OFF).rule.minutes).toBe(480);
  });
});

describe('CSV reading', () => {
  it('strips a BOM and tolerates CRLF', () => {
    const text = '\uFEFFdate,tableName,tableValue,minimum,ideal,estimated,start,end\r\n' +
      '2026-03-02,Team,T1,2,0,0,09:00,13:00\r\n';
    const { header, rows } = core.readRows(text);
    expect(header[0]).toBe('date');
    expect(rows).toHaveLength(1);
  });

  it('skips comment and blank lines', () => {
    const text = '# a note\n\ndate,tableName,tableValue,minimum,ideal,estimated,start,end\n' +
      '# another\n2026-03-02,Team,T1,1,0,0,09:00,13:00\n';
    const { header, rows } = core.readRows(text);
    expect(header[0]).toBe('date');
    expect(rows).toHaveLength(1);
  });

  it('keeps a quoted decimal comma in one column', () => {
    const { rows } = core.readRows('employee_id,2026-01-01\nNL1,"7,2"\n');
    expect(rows[0]['2026-01-01']).toBe('7,2');
  });

  it('uses the grain it is given', () => {
    const text = 'date,tableName,tableValue,minimum,ideal,estimated,start,end\n' +
      '2026-03-02,Team,T1,1,0,0,09:00,13:00\n';
    const periods = core.readDemand(text, 'periods');
    expect(periods.rows).toHaveLength(1);
    expect(periods.problems).toEqual([]);
    const shifts = core.readDemand(text, 'shifts');
    expect(shifts.rows).toEqual([]);
    expect(shifts.problems.some((p) => p.includes('workPeriod'))).toBe(true);
  });

  it.each([
    ['not-a-date,Team,T1,1,0,0,09:00,13:00', "bad date 'not-a-date'"],
    ['2026-03-02,Team,T1,x,0,0,09:00,13:00', 'minimum is not a number'],
    ['2026-03-02,Team,T1,1,0,0,9am,13:00', 'bad window']
  ])('reports a bad row and keeps going (%s)', (row, needle) => {
    const text = `date,tableName,tableValue,minimum,ideal,estimated,start,end\n${row}\n` +
      '2026-03-03,Team,T1,1,0,0,09:00,13:00\n';
    const { rows, problems } = core.readDemand(text, 'periods');
    expect(problems.some((p) => p.includes(needle))).toBe(true);
    expect(rows.length).toBeGreaterThan(0);
  });

  it('reads a float minimum and a midnight window', () => {
    const text = 'date,tableName,tableValue,minimum,ideal,estimated,start,end\n' +
      '2026-03-02,Team,T1,4.5,0,0,22:00,06:00\n';
    const [row] = core.readDemand(text, 'periods').rows;
    expect(row.minimum).toBe(4.5);
    expect(row.window).toEqual(iv(1320, 1800));
  });

  it('requires the employee_id column', () => {
    const { cells, dates, problems } = core.readScheduleInput('emp,2026-03-02\nEMP001,8\n');
    expect(problems[0]).toBe("first column must be 'employee_id', found ['emp']");
    expect(cells.size).toBe(0);
    expect(dates).toEqual([]);
  });

  it('flags a non-date column and a repeated row', () => {
    const { problems } = core.readScheduleInput('employee_id,2026-03-02,monday\nEMP001,8,8\nEMP001,4,4\n');
    expect(problems.some((p) => p.includes('not a YYYY-MM-DD date'))).toBe(true);
    expect(problems.some((p) => p.includes('appears twice'))).toBe(true);
  });

  it('keeps numeric-looking employee ids in file order', () => {
    const { cells } = core.readScheduleInput('employee_id,2026-01-01\n900027719,8\n20072412,DO\n');
    expect([...cells.keys()]).toEqual(['900027719', '20072412']);
  });

  it('reports a bad code and a duplicate in the menu', () => {
    const { catalogue, problems } = core.readSchedules(
      'code,description,scheduleWeightMinutes,startMin,endMin\n' +
      'nine,09:00-13:00,240,540,780\n9001,09:00-13:00,240,540,780\n9001,10:00-14:00,240,600,840\n'
    );
    expect(problems.some((p) => p.includes('not an integer'))).toBe(true);
    expect(problems.some((p) => p.includes('appears twice'))).toBe(true);
    expect([...catalogue.keys()]).toEqual([9001]);
  });

  it('recognises a rest sentinel from the data', () => {
    const { catalogue } = core.readSchedules(
      'code,description,scheduleWeightMinutes,startMin,endMin\n3,Day off,0,,\n9001,09:00-13:00,240,540,780\n'
    );
    expect(catalogue.get(3).isSentinel).toBe(true);
    expect(catalogue.get(9001).isSentinel).toBe(false);
  });
});

describe('dates', () => {
  it('treats an open-ended assignment as covering any later day', () => {
    const entry = { start: '2024-01-01', end: null };
    expect(core.covers(entry, '2030-06-01')).toBe(true);
    expect(core.covers(entry, '2023-01-01')).toBe(false);
  });

  it.each(['2026-01-05', '2026-01-05T00:00:00', '2026-01-05T09:00:00Z'])(
    'iso accepts %s', (text) => {
      expect(core.iso(text)).toBe('2026-01-05');
    }
  );

  it('iso rejects impossible dates', () => {
    expect(core.iso('2026-02-30')).toBeNull();
    expect(core.iso('monday')).toBeNull();
  });

  it('computes the week index case-insensitively from weekStart', () => {
    const origin = '2026-01-01'; // a Thursday
    expect(core.weekIndex('2026-01-04', origin, 'Monday')).toBe(0);
    expect(core.weekIndex('2026-01-05', origin, 'monday')).toBe(1);
    expect(() => core.weekIndex(origin, origin, 'caturday')).toThrow(core.DomainError);
  });

  it('builds an empty horizon when the scope is reversed', () => {
    expect(core.horizon({ temporalScope: { start: '2026-03-08', end: '2026-03-02' } })).toEqual([]);
    expect(core.horizon({ temporalScope: { start: '2026-03-02', end: '2026-03-08' } })).toHaveLength(7);
  });

  it('neither duplicates nor skips a date across the Lisbon DST change', () => {
    const days = core.dateRange('2026-03-27', '2026-04-01');
    expect(days).toEqual([
      '2026-03-27', '2026-03-28', '2026-03-29', '2026-03-30', '2026-03-31', '2026-04-01'
    ]);
    expect(core.dateRange('2026-10-24', '2026-10-27')).toHaveLength(4);
  });

  it('knows the weekday', () => {
    expect(core.weekdayName('2026-01-01')).toBe('thursday');
    expect(core.weekday('2026-03-02')).toBe(0);
  });
});

describe('feasibility', () => {
  const problem = {
    timeGrid: { slotMinutes: 30 },
    contracts: { definitions: [{ id: 'FT', workMinutesPerDay: 480 }, { id: 'NL', workMinutesPerDay: 432 }] },
    employees: {
      list: [
        { id: 'E1', contractAssignments: [{ contractType: 'FT', start: '2026-03-02', end: '2026-03-02' }] },
        { id: 'E2', contractAssignments: [{ contractType: 'NL', start: '2026-03-01', end: null }] }
      ]
    },
    ...DAY_OFF
  };
  const input = core.readScheduleInput(
    'employee_id,2026-03-02,2026-03-03\nE1,EQUALS:09:10-13:00,A\nE2,A,DO\n'
  );

  it('finds every impossible worker-day', () => {
    const reasons = core.scanFeasibility(problem, input).map(core.diagnosticToString);
    expect(reasons).toEqual([
      "E1 on 2026-03-02: cell 'EQUALS:09:10-13:00' - window 09:10-13:00 does not land on the 30-minute grid",
      "E1 on 2026-03-03: cell 'A' - asks for work on a day no contract covers",
      "E2 on 2026-03-02: cell 'A' - 432 min is not a multiple of the 30-minute grid"
    ]);
  });
});
