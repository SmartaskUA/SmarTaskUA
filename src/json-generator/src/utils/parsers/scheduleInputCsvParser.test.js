import { describe, it, expect } from 'vitest';
import { parseScheduleInputCsv } from './scheduleInputCsvParser';

const EMPLOYEES = [{ id: 'E1', name: 'Alice' }, { id: 'E2', name: 'Bob' }];
const DATES = ['2030-01-01', '2030-01-02'];

describe('parseScheduleInputCsv', () => {
  it('resolves { dataMatrix, errors } for a valid CSV', async () => {
    const csv = 'employee_id,2030-01-01,2030-01-02\nE1,A,8\nE2,VAC,NOT';
    const { dataMatrix, errors } = await parseScheduleInputCsv(csv, EMPLOYEES, DATES);
    expect(errors).toEqual([]);
    expect(dataMatrix).toEqual({
      E1: { '2030-01-01': 'A', '2030-01-02': '8' },
      E2: { '2030-01-01': 'VAC', '2030-01-02': 'NOT' }
    });
  });

  it('returns dataMatrix: null when the employee_id column is missing', async () => {
    const csv = 'emp,2030-01-01\nE1,A';
    const { dataMatrix, errors } = await parseScheduleInputCsv(csv, EMPLOYEES, DATES);
    expect(dataMatrix).toBeNull();
    expect(errors.join(' ')).toMatch(/employee_id/);
  });

  it('errors and skips a row with a missing employee id (index+1)', async () => {
    const csv = 'employee_id,2030-01-01\n,A';
    const { dataMatrix, errors } = await parseScheduleInputCsv(csv, EMPLOYEES, DATES);
    expect(errors.join(' ')).toMatch(/Row 1: Missing employee ID/);
    expect(dataMatrix).toEqual({});
  });

  it('errors and skips an unknown employee id', async () => {
    const csv = 'employee_id,2030-01-01\nZZZ,A';
    const { dataMatrix, errors } = await parseScheduleInputCsv(csv, EMPLOYEES, DATES);
    expect(errors.join(' ')).toMatch(/Unknown employee ID "ZZZ"/);
    expect(dataMatrix).toEqual({});
  });

  it('produces a sparse matrix (empty cells omitted) but keeps the - placeholder', async () => {
    const csv = 'employee_id,2030-01-01,2030-01-02\nE1,,-';
    const { dataMatrix } = await parseScheduleInputCsv(csv, EMPLOYEES, DATES);
    // 01-01 empty → omitted; 01-02 '-' → kept
    expect(dataMatrix.E1).toEqual({ '2030-01-02': '-' });
  });

  it('preserves time-constraint and hour tokens', async () => {
    const csv = 'employee_id,2030-01-01,2030-01-02\nE1,EQUALS:08:00-16:00,12';
    const { dataMatrix } = await parseScheduleInputCsv(csv, EMPLOYEES, DATES);
    expect(dataMatrix.E1).toEqual({ '2030-01-01': 'EQUALS:08:00-16:00', '2030-01-02': '12' });
  });

  it('flags an invalid date-column header', async () => {
    const csv = 'employee_id,NOTADATE\nE1,A';
    const { errors } = await parseScheduleInputCsv(csv, EMPLOYEES, DATES);
    expect(errors.join(' ')).toMatch(/Invalid date format "NOTADATE"/);
  });

  it('[characterization] does NOT filter dates outside the provided dateRange (param unused)', async () => {
    const csv = 'employee_id,2999-12-31\nE1,A'; // date not in DATES
    const { dataMatrix } = await parseScheduleInputCsv(csv, EMPLOYEES, DATES);
    expect(dataMatrix.E1).toEqual({ '2999-12-31': 'A' });
  });
});
