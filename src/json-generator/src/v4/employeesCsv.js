/**
 * The wizard's employee roster CSV — a convenience format, not part of v4:
 *
 *   employee_id,name,contract_type,competencies
 *   EMP001,Ana,FT_8h,"Team/T1:1,Responsibility/A:2"
 *
 * `competencies` lists tableName/tableValue:level, level 1 being the highest
 * (and the default). Imported assignments run open-ended from the horizon's start.
 */

import { writeCsv } from './generate';
import { activeContract, pairKey } from './core';

export const EMPLOYEE_CSV_FIELDS = ['employee_id', 'name', 'contract_type', 'competencies'];
export const EMPLOYEE_CSV_REQUIRED = ['employee_id', 'contract_type'];

/** [{tableName, tableValue, level}] from "Team/T1:1,Responsibility/A:2", or throws with the bad token. */
export function parseCompetencies(spec) {
  return String(spec || '').split(/[,;]/).map((t) => t.trim()).filter(Boolean).map((token) => {
    const colon = token.lastIndexOf(':');
    const pair = colon > 0 ? token.slice(0, colon) : token;
    const levelText = colon > 0 ? token.slice(colon + 1).trim() : '1';
    const slash = pair.indexOf('/');
    if (slash <= 0 || slash === pair.length - 1) throw new Error(`"${token}" is not tableName/tableValue[:level]`);
    const level = Number(levelText);
    if (!Number.isInteger(level) || level < 1) throw new Error(`"${token}": level must be a whole number ≥ 1`);
    return { tableName: pair.slice(0, slash).trim(), tableValue: pair.slice(slash + 1).trim(), level };
  });
}

export function formatCompetencies(assignments) {
  return (assignments || []).map((a) => `${a.tableName}/${a.tableValue}:${a.level}`).join(',');
}

/**
 * Employees from mapped CSV rows. Returns {employees, warnings}; a row that
 * cannot be imported is skipped with a warning naming the row.
 */
export function employeesFromRows(rows, mapping, state) {
  const contracts = new Set(state.contracts.definitions.map((c) => c.id));
  const declared = new Set(state.demand.dimensions.map((d) => pairKey(d.tableName, d.tableValue)));
  const taken = new Set(state.employees.list.map((e) => e.id));
  const start = state.temporalScope.start || '';
  const employees = [];
  const warnings = [];

  rows.forEach((row, index) => {
    const n = index + 1;
    const get = (field) => String(mapping[field] ? row[mapping[field]] ?? '' : '').trim();
    const id = get('employee_id');
    const contract = get('contract_type');
    if (!id) return warnings.push(`Row ${n}: employee_id is empty — skipped`);
    if (taken.has(id)) return warnings.push(`Row ${n}: ${id} already exists — skipped`);
    if (!contracts.has(contract)) return warnings.push(`Row ${n}: unknown contract "${contract}" — skipped`);
    let competencies;
    try {
      competencies = parseCompetencies(get('competencies'));
    } catch (exc) {
      return warnings.push(`Row ${n}: ${exc.message} — skipped`);
    }
    const undeclared = competencies.filter((c) => !declared.has(pairKey(c.tableName, c.tableValue)));
    if (undeclared.length) {
      return warnings.push(`Row ${n}: ${undeclared.map((c) => `${c.tableName}/${c.tableValue}`).join(', ')} not declared in Dimensions — skipped`);
    }
    taken.add(id);
    employees.push({
      id,
      name: get('name'),
      contractAssignments: [{ contractType: contract, start, end: null }],
      competencyAssignments: competencies.map((c) => ({ ...c, start, end: null }))
    });
    return null;
  });
  return { employees, warnings };
}

/** The roster as CSV. The contract column is the one active on the horizon's first day. */
export function employeesToCsv(state) {
  const day = state.temporalScope.start;
  return writeCsv(EMPLOYEE_CSV_FIELDS, state.employees.list.map((e) => [
    e.id,
    e.name || '',
    activeContract(e, day) || e.contractAssignments?.[0]?.contractType || '',
    formatCompetencies(e.competencyAssignments)
  ]));
}

/** A one-row template that uses the problem's own contracts and dimensions. */
export function employeesTemplateCsv(state) {
  const contract = state.contracts.definitions[0]?.id || 'FT_8h';
  const dims = state.demand.dimensions.slice(0, 2);
  const comps = dims.length ? dims.map((d, i) => `${d.tableName}/${d.tableValue}:${i + 1}`).join(',') : 'Team/T1:1';
  return writeCsv(EMPLOYEE_CSV_FIELDS, [['EMP001', 'Jane Doe', contract, comps]]);
}
