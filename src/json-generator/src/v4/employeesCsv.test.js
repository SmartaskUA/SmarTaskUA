// @vitest-environment node
import { describe, it, expect } from 'vitest';
import { employeesFromRows, employeesToCsv, parseCompetencies } from './employeesCsv';
import { sampleState } from './fixtures/sampleState';
import { readRows } from './core';

const MAPPING = { employee_id: 'employee_id', name: 'name', contract_type: 'contract_type', competencies: 'competencies' };

describe('employee roster CSV', () => {
  it('parses competencies with a default level of 1', () => {
    expect(parseCompetencies('Team/T1:2, Responsibility/A')).toEqual([
      { tableName: 'Team', tableValue: 'T1', level: 2 },
      { tableName: 'Responsibility', tableValue: 'A', level: 1 }
    ]);
    expect(() => parseCompetencies('T1:1')).toThrow(/tableName\/tableValue/);
    expect(() => parseCompetencies('Team/T1:0')).toThrow(/level/);
  });

  it('round-trips the roster through CSV', () => {
    const s = sampleState();
    const { rows } = readRows(employeesToCsv(s));
    const fresh = { ...s, employees: { list: [] } };
    const { employees, warnings } = employeesFromRows(rows, MAPPING, fresh);
    expect(warnings).toEqual([]);
    expect(employees.map((e) => e.id)).toEqual(['EMP001', 'EMP002', 'EMP003', 'EMP004']);
    expect(employees[0].competencyAssignments).toEqual([
      { tableName: 'Team', tableValue: 'T1', level: 1, start: '2026-03-02', end: null },
      { tableName: 'Responsibility', tableValue: 'A', level: 1, start: '2026-03-02', end: null }
    ]);
  });

  it('skips rows it cannot import, saying why', () => {
    const rows = [
      { employee_id: 'EMP001', contract_type: 'FT_8h' },
      { employee_id: 'NEW1', contract_type: 'NOPE' },
      { employee_id: 'NEW2', contract_type: 'FT_8h', competencies: 'Piso/T1:1' },
      { employee_id: 'NEW3', contract_type: 'PT_4h', competencies: 'Team/T1' }
    ];
    const { employees, warnings } = employeesFromRows(rows, MAPPING, sampleState());
    expect(employees.map((e) => e.id)).toEqual(['NEW3']);
    expect(warnings).toEqual([
      'Row 1: EMP001 already exists — skipped',
      'Row 2: unknown contract "NOPE" — skipped',
      'Row 3: Piso/T1 not declared in Dimensions — skipped'
    ]);
  });
});
