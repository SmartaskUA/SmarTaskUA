import { describe, it, expect } from 'vitest';
import { generateScheduleInputCsv } from './scheduleInputCsvGenerator';

const EMPLOYEES = [{ id: 'E1', name: 'Alice' }, { id: 'E2', name: 'Bob' }];
const DATES = ['2030-01-01', '2030-01-02'];

function parse(csv) {
  return csv.trim().split('\n').map((l) => l.replace(/\r$/, '').split(','));
}

describe('generateScheduleInputCsv', () => {
  it('throws when there are no employees', () => {
    expect(() => generateScheduleInputCsv([], {}, DATES)).toThrow(/No employees/);
  });

  it('throws when there is no date range', () => {
    expect(() => generateScheduleInputCsv(EMPLOYEES, {}, [])).toThrow(/No date range/);
  });

  it('emits employee_id + one column per date', () => {
    const csv = generateScheduleInputCsv(EMPLOYEES, {}, DATES);
    const [header] = parse(csv);
    expect(header).toEqual(['employee_id', '2030-01-01', '2030-01-02']);
  });

  it('produces a dense grid: one row per employee, missing cells empty', () => {
    const matrix = { E1: { '2030-01-01': 'A' } };
    const [, r1, r2] = parse(generateScheduleInputCsv(EMPLOYEES, matrix, DATES));
    expect(r1).toEqual(['E1', 'A', '']); // E1 has 01-01, missing 01-02
    expect(r2).toEqual(['E2', '', '']); // E2 entirely empty
  });

  it('writes all cell tokens verbatim (A, hours, VAC, NOT, constraints, - placeholder)', () => {
    const matrix = {
      E1: { '2030-01-01': 'A', '2030-01-02': '8' },
      E2: { '2030-01-01': 'EQUALS:08:00-16:00', '2030-01-02': '-' }
    };
    const csv = generateScheduleInputCsv(EMPLOYEES, matrix, DATES);
    expect(csv).toContain('E1,A,8');
    // constraint value contains a comma-free colon token; ensure it is present intact
    expect(csv).toContain('EQUALS:08:00-16:00');
    expect(csv).toMatch(/E2,EQUALS:08:00-16:00,-/);
  });
});
