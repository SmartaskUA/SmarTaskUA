import { describe, it, expect } from 'vitest';
import {
  generateDemandCsv,
  generateDefaultDemandData,
  fillMissingDemandEntries
} from './demandCsvGenerator';

const WPS = [
  { code: 'M', name: 'Morning', timeRange: { start: '08:00', end: '16:00' } },
  { code: 'N', name: 'Night', timeRange: { start: '22:00', end: '06:30' } }
];

// Parse a CSV string into { header, rows } for structural assertions.
function rows(csv) {
  const lines = csv.trim().split('\n').map((l) => l.replace(/\r$/, ''));
  return { header: lines[0], data: lines.slice(1) };
}

describe('generateDemandCsv', () => {
  it('returns a header-only string (8 columns, trailing newline) for empty data', () => {
    const csv = generateDemandCsv([], 'team', WPS);
    expect(csv).toBe('date,workPeriod,team,minimum,ideal,estimated,start,end\n');
  });

  it('uses the competency column name for the competency model', () => {
    const csv = generateDemandCsv([], 'competency', WPS);
    expect(csv).toBe('date,workPeriod,competency,minimum,ideal,estimated,start,end\n');
  });

  it('emits the fixed 8-column order with a team entry', () => {
    const data = [{ date: '2030-01-01', workPeriod: 'M', team: 'TeamA', minimum: 1, ideal: 2, estimated: 1 }];
    const { header } = rows(generateDemandCsv(data, 'team', WPS));
    expect(header).toBe('date,workPeriod,team,minimum,ideal,estimated,start,end');
  });

  it('leaves start/end empty when the entry time equals the work-period default', () => {
    const data = [{ date: '2030-01-01', workPeriod: 'M', team: 'TeamA', minimum: 1, ideal: 2, estimated: 1, timeRange: { start: '08:00', end: '16:00' } }];
    const { data: [row] } = rows(generateDemandCsv(data, 'team', WPS));
    expect(row).toBe('2030-01-01,M,TeamA,1,2,1,,');
  });

  it('writes start/end only when the entry time overrides the work-period default', () => {
    const data = [{ date: '2030-01-01', workPeriod: 'M', team: 'TeamA', minimum: 1, ideal: 2, estimated: 1, timeRange: { start: '06:00', end: '14:00' } }];
    const { data: [row] } = rows(generateDemandCsv(data, 'team', WPS));
    expect(row).toBe('2030-01-01,M,TeamA,1,2,1,06:00,14:00');
  });

  it('leaves start/end empty when workPeriods is empty (no default to diff against)', () => {
    const data = [{ date: '2030-01-01', workPeriod: 'M', team: 'TeamA', minimum: 1, ideal: 2, estimated: 1, timeRange: { start: '06:00', end: '14:00' } }];
    const { data: [row] } = rows(generateDemandCsv(data, 'team', []));
    expect(row).toBe('2030-01-01,M,TeamA,1,2,1,,');
  });

  it('leaves start/end empty when the work period is not found', () => {
    const data = [{ date: '2030-01-01', workPeriod: 'ZZ', team: 'TeamA', minimum: 1, ideal: 2, estimated: 1, timeRange: { start: '06:00', end: '14:00' } }];
    const { data: [row] } = rows(generateDemandCsv(data, 'team', WPS));
    expect(row).toBe('2030-01-01,ZZ,TeamA,1,2,1,,');
  });

  it('sorts by date, then workPeriod, then team', () => {
    const data = [
      { date: '2030-01-02', workPeriod: 'M', team: 'TeamA', minimum: 1, ideal: 1, estimated: 1 },
      { date: '2030-01-01', workPeriod: 'N', team: 'TeamB', minimum: 1, ideal: 1, estimated: 1 },
      { date: '2030-01-01', workPeriod: 'N', team: 'TeamA', minimum: 1, ideal: 1, estimated: 1 },
      { date: '2030-01-01', workPeriod: 'M', team: 'TeamA', minimum: 1, ideal: 1, estimated: 1 }
    ];
    const { data: out } = rows(generateDemandCsv(data, 'team', WPS));
    expect(out.map((r) => r.split(',').slice(0, 3).join(','))).toEqual([
      '2030-01-01,M,TeamA',
      '2030-01-01,N,TeamA',
      '2030-01-01,N,TeamB',
      '2030-01-02,M,TeamA'
    ]);
  });

  // Characterization: only the team field is null-guarded in the sort comparator,
  // so an entry with an undefined date throws. Pins current (fragile) behavior.
  it('[characterization] throws when an entry has an undefined date', () => {
    const data = [
      { date: '2030-01-01', workPeriod: 'M', team: 'TeamA', minimum: 1, ideal: 1, estimated: 1 },
      { workPeriod: 'M', team: 'TeamB', minimum: 1, ideal: 1, estimated: 1 }
    ];
    expect(() => generateDemandCsv(data, 'team', WPS)).toThrow();
  });
});

describe('generateDefaultDemandData', () => {
  it('builds the cartesian product of dates x workPeriods x teams', () => {
    const out = generateDefaultDemandData(
      ['2030-01-01', '2030-01-02'],
      [{ code: 'M' }, { code: 'N' }],
      [{ code: 'TeamA' }],
      { minimum: 2, ideal: 3, estimated: 2 },
      'team'
    );
    expect(out).toHaveLength(4);
    expect(out[0]).toEqual({ date: '2030-01-01', workPeriod: 'M', team: 'TeamA', minimum: 2, ideal: 3, estimated: 2 });
  });

  it('[characterization] coerces a 0 default to 1 (|| 1)', () => {
    const out = generateDefaultDemandData(['2030-01-01'], [{ code: 'M' }], [{ code: 'TeamA' }], { minimum: 0, ideal: 0, estimated: 0 }, 'team');
    expect(out[0]).toMatchObject({ minimum: 1, ideal: 1, estimated: 1 });
  });

  it('uses the competency field for the competency model', () => {
    const out = generateDefaultDemandData(['2030-01-01'], [{ code: 'M' }], [{ code: 'Nurse' }], {}, 'competency');
    expect(out[0]).toMatchObject({ competency: 'Nurse' });
    expect(out[0].team).toBeUndefined();
  });
});

describe('fillMissingDemandEntries', () => {
  it('preserves existing entries (including timeRange) and appends only missing combos', () => {
    const existing = [{ date: '2030-01-01', workPeriod: 'M', team: 'TeamA', minimum: 5, ideal: 5, estimated: 5, timeRange: { start: '06:00', end: '14:00' } }];
    const out = fillMissingDemandEntries(
      existing,
      ['2030-01-01'],
      [{ code: 'M' }, { code: 'N' }],
      [{ code: 'TeamA' }],
      { minimum: 1, ideal: 1, estimated: 1 },
      'team'
    );
    expect(out).toHaveLength(2);
    // original kept verbatim
    expect(out[0]).toEqual(existing[0]);
    // missing M/N combo filled with defaults
    expect(out[1]).toMatchObject({ date: '2030-01-01', workPeriod: 'N', team: 'TeamA', minimum: 1 });
  });
});
