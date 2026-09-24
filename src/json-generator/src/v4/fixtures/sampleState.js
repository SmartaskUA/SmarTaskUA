/**
 * A problem authored the way the wizard builds one — weekly template applied,
 * matrix auto-filled then edited, menu generated from contracts — rather than
 * imported. Used by the tests and by scripts/validate-with-python.mjs.
 */

import { createInitialState } from '../state';
import { applyTemplate, fillMatrix, generateMenuRows } from '../operations';

const block = (id, tableName, tableValue, start, end, minimum) =>
  ({ id, tableName, tableValue, start, end, minimum, ideal: 0, estimated: 0 });

export function sampleState() {
  let s = createInitialState();
  s.metadata = { ...s.metadata, problemId: 'SAMPLE_MARCH_2026', rosterCode: 'SAMPLE', createdAt: '2026-03-01T09:00:00Z', description: 'Authored in the wizard' };
  s.temporalScope = { start: '2026-03-02', end: '2026-03-08' };
  s.calendar = { weekStart: 'monday', holidays: [{ date: '2026-03-05', code: 'TPL', name: 'Template Day', hasEve: true }] };
  s.contracts.definitions = [
    { id: 'FT_8h', name: 'Full time', workMinutesPerDay: 480 },
    { id: 'PT_4h', name: 'Part time', workMinutesPerDay: 240 }
  ];
  s.demand.dimensions = [
    { tableName: 'Team', tableValue: 'T1', name: 'Team 1' },
    { tableName: 'Responsibility', tableValue: 'A', name: 'Floor A' }
  ];
  const open = (id, tn, tv, level, contract) => ({
    id,
    name: id,
    contractAssignments: [{ contractType: contract, start: '2024-01-01', end: null }],
    competencyAssignments: [
      { tableName: 'Team', tableValue: 'T1', level, start: '2024-01-01', end: null },
      ...(tn ? [{ tableName: tn, tableValue: tv, level, start: '2024-01-01', end: null }] : [])
    ]
  });
  s.employees.list = [
    open('EMP001', 'Responsibility', 'A', 1, 'FT_8h'),
    open('EMP002', 'Responsibility', 'A', 2, 'FT_8h'),
    open('EMP003', null, null, 3, 'PT_4h'),
    open('EMP004', null, null, 4, 'PT_4h')
  ];
  const weekday = [
    block('b1', 'Team', 'T1', '09:00', '13:00', 2),
    block('b2', 'Team', 'T1', '13:00', '17:00', 2),
    block('b3', 'Responsibility', 'A', '09:00', '17:00', 1)
  ];
  const weekend = [
    block('b4', 'Team', 'T1', '09:00', '13:00', 1),
    block('b5', 'Responsibility', 'A', '09:00', '13:00', 1)
  ];
  s.demand.weeklyTemplate = {
    monday: weekday, tuesday: weekday, wednesday: weekday, thursday: weekday, friday: weekday,
    saturday: weekend, sunday: weekend
  };
  s = applyTemplate(s);
  s = fillMatrix(s);
  const cells = {
    EMP001: { '2026-03-06': 'DO', '2026-03-07': 'DO' },
    EMP002: { '2026-03-02': '8', '2026-03-04': 'VAC', '2026-03-05': 'VAC' },
    EMP003: { '2026-03-02': '4', '2026-03-04': 'DO', '2026-03-07': 'NOT' },
    EMP004: { '2026-03-03': 'WITHIN:09:00-17:00', '2026-03-05': 'DO', '2026-03-07': 'DO' }
  };
  for (const [eid, row] of Object.entries(cells)) Object.assign(s.scheduleInput.dataMatrix[eid], row);
  s.schedules.rows = [...s.schedules.rows, ...generateMenuRows(s, { stride: 240 })];
  s.priorityHierarchy = [
    { rank: 1, label: 'TEAM', tableName: 'Team', tableValue: 'T1', maxAlarmTableType: 'MaxAlarmLevel_Estimate_Ideal_Minimum', generationSequenceType: 'BY_LEVEL', minAbilityLevel: 1, maxAbilityLevel: 9, alarmLevelPercentage: 100 },
    { rank: 2, label: 'RESPONSIBILITY', tableName: 'Responsibility', tableValue: 'A', maxAlarmTableType: 'MaxAlarmLevel_Estimate_Ideal_Minimum', generationSequenceType: 'BY_ALARM_TABLE', minAbilityLevel: 1, maxAbilityLevel: 9, alarmLevelPercentage: 100 }
  ];
  s.constraints = {
    hard: [{
      id: 'LEGISLATION-1',
      type: 'RosterLegislation',
      parameters: { MaxConsecutiveWorkDays: 6, MaxConsecutiveWorkDaysInWeek: 6, MinDistanceBetweenShiftsInMinutes: 660 },
      startDate: '2026-03-02T00:00:00',
      enabled: true
    }],
    soft: []
  };
  return s;
}
