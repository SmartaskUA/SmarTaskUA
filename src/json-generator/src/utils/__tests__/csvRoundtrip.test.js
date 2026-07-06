// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  generateDemandCsv,
  downloadDemandCsv
} from '../generators/demandCsvGenerator';
import { parseDemandCsvFromText } from '../parsers/demandCsvParser';
import {
  generateScheduleInputCsv,
  downloadScheduleInputCsv
} from '../generators/scheduleInputCsvGenerator';
import { parseScheduleInputCsv } from '../parsers/scheduleInputCsvParser';

const WPS = [
  { code: 'M', name: 'Morning', timeRange: { start: '08:00', end: '16:00' } },
  { code: 'N', name: 'Night', timeRange: { start: '22:00', end: '06:30' } }
];

describe('demand round-trip (generate -> parseText -> generate)', () => {
  it('is stable for plain rows and normalizes ordering', async () => {
    const data = [
      { date: '2030-01-02', workPeriod: 'M', team: 'TeamA', minimum: 1, ideal: 2, estimated: 1 },
      { date: '2030-01-01', workPeriod: 'M', team: 'TeamA', minimum: 3, ideal: 4, estimated: 3 }
    ];
    const csv1 = generateDemandCsv(data, 'team', WPS);
    const { data: parsed } = await parseDemandCsvFromText(csv1, 'team');
    const csv2 = generateDemandCsv(parsed, 'team', WPS);
    expect(csv2).toBe(csv1); // second pass identical (already sorted)
    // and the parse produced sorted-by-date output
    expect(parsed.map((e) => e.date)).toEqual(['2030-01-01', '2030-01-02']);
  });

  it('preserves a genuine override across the round-trip', async () => {
    const data = [{ date: '2030-01-01', workPeriod: 'M', team: 'TeamA', minimum: 1, ideal: 2, estimated: 1, timeRange: { start: '06:00', end: '14:00' } }];
    const { data: parsed } = await parseDemandCsvFromText(generateDemandCsv(data, 'team', WPS), 'team');
    expect(parsed[0].timeRange).toEqual({ start: '06:00', end: '14:00' });
  });

  it('drops a timeRange that equals the work-period default (written empty, not reconstructed)', async () => {
    const data = [{ date: '2030-01-01', workPeriod: 'M', team: 'TeamA', minimum: 1, ideal: 2, estimated: 1, timeRange: { start: '08:00', end: '16:00' } }];
    const { data: parsed } = await parseDemandCsvFromText(generateDemandCsv(data, 'team', WPS), 'team');
    expect(parsed[0].timeRange).toBeUndefined();
  });
});

describe('schedule-input round-trip (generate -> parse -> generate)', () => {
  const employees = [{ id: 'E1' }, { id: 'E2' }];
  const dates = ['2030-01-01', '2030-01-02'];

  it('is stable across dense<->sparse and preserves all tokens', async () => {
    const matrix = {
      E1: { '2030-01-01': 'A', '2030-01-02': '8' },
      E2: { '2030-01-01': 'EQUALS:08:00-16:00', '2030-01-02': '-' }
    };
    const csv1 = generateScheduleInputCsv(employees, matrix, dates);
    const { dataMatrix } = await parseScheduleInputCsv(csv1, employees, dates);
    const csv2 = generateScheduleInputCsv(employees, dataMatrix, dates);
    expect(csv2).toBe(csv1);
    expect(dataMatrix.E2['2030-01-02']).toBe('-');
  });
});

describe('download helpers (jsdom + stubbed URL.createObjectURL)', () => {
  let created;
  let clicked;

  beforeEach(() => {
    created = [];
    clicked = 0;
    // jsdom does not implement createObjectURL/revokeObjectURL
    vi.stubGlobal('URL', {
      ...URL,
      createObjectURL: (blob) => { created.push(blob); return 'blob:mock'; },
      revokeObjectURL: () => {}
    });
    // count anchor clicks without navigating
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function () { clicked += 1; });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  // jsdom's Blob has no usable .text(); read it via FileReader instead.
  function blobText(blob) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(reader.error);
      reader.readAsText(blob);
    });
  }

  it('downloadDemandCsv emits a Blob whose text matches the generator and triggers a click', async () => {
    const data = [{ date: '2030-01-01', workPeriod: 'M', team: 'TeamA', minimum: 1, ideal: 2, estimated: 1 }];
    downloadDemandCsv(data, 'team', 'demand.csv', WPS);
    expect(clicked).toBe(1);
    expect(created).toHaveLength(1);
    const text = await blobText(created[0]);
    expect(text).toBe(generateDemandCsv(data, 'team', WPS));
  });

  it('downloadScheduleInputCsv emits a matching Blob and triggers a click', async () => {
    const employees = [{ id: 'E1' }];
    const dates = ['2030-01-01'];
    const matrix = { E1: { '2030-01-01': 'A' } };
    downloadScheduleInputCsv(employees, matrix, dates, 'schedule_input.csv');
    expect(clicked).toBe(1);
    const text = await blobText(created[0]);
    expect(text).toBe(generateScheduleInputCsv(employees, matrix, dates));
  });
});
