// @vitest-environment jsdom
import { describe, it, expect } from 'vitest';
import { parseDemandCsv, parseDemandCsvFromText } from './demandCsvParser';

// Build a File from CSV text (parseDemandCsv consumes a File via Papa.parse).
function csvFile(text, name = 'demand.csv') {
  return new File([text], name, { type: 'text/csv' });
}

const HEADER = 'date,workPeriod,team,minimum,ideal,estimated,start,end';

describe('parseDemandCsv (File, strict)', () => {
  it('parses valid rows into entries', async () => {
    const { data, errors } = await parseDemandCsv(csvFile(`${HEADER}\n2030-01-01,M,TeamA,1,2,1,,`), 'team');
    expect(errors).toEqual([]);
    expect(data).toHaveLength(1);
    expect(data[0]).toMatchObject({ date: '2030-01-01', workPeriod: 'M', team: 'TeamA', minimum: 1, ideal: 2, estimated: 1 });
    expect(data[0].timeRange).toBeUndefined();
  });

  it('reports a missing required column and returns no data', async () => {
    // no "estimated" column
    const { data, errors } = await parseDemandCsv(csvFile('date,workPeriod,team,minimum,ideal\n2030-01-01,M,TeamA,1,2'), 'team');
    expect(data).toEqual([]);
    expect(errors.join(' ')).toMatch(/Missing required columns/);
  });

  it('returns no error for a header-only (empty) file', async () => {
    const { data, errors } = await parseDemandCsv(csvFile(`${HEADER}\n`), 'team');
    expect(data).toEqual([]);
    expect(errors).toEqual([]);
  });

  it('defaults absent numeric cells to 0', async () => {
    const { data } = await parseDemandCsv(csvFile('date,workPeriod,team,minimum,ideal,estimated\n2030-01-01,M,TeamA,,,'), 'team');
    expect(data[0]).toMatchObject({ minimum: 0, ideal: 0, estimated: 0 });
  });

  it('[characterization] keeps a NaN entry but also records an error for non-numeric input', async () => {
    const { data, errors } = await parseDemandCsv(csvFile('date,workPeriod,team,minimum,ideal,estimated\n2030-01-01,M,TeamA,abc,2,1'), 'team');
    expect(data).toHaveLength(1);
    expect(Number.isNaN(data[0].minimum)).toBe(true);
    expect(errors.join(' ')).toMatch(/Invalid minimum/);
  });

  it('flags a bad date format', async () => {
    const { errors } = await parseDemandCsv(csvFile('date,workPeriod,team,minimum,ideal,estimated\n01-01-2030,M,TeamA,1,2,1'), 'team');
    expect(errors.join(' ')).toMatch(/Invalid date format/);
  });

  it('uses index+2 line numbers in errors', async () => {
    const { errors } = await parseDemandCsv(csvFile('date,workPeriod,team,minimum,ideal,estimated\nBAD,M,TeamA,1,2,1'), 'team');
    expect(errors.join(' ')).toMatch(/Line 2/);
  });

  it('reads a valid per-day override into timeRange', async () => {
    const { data } = await parseDemandCsv(csvFile(`${HEADER}\n2030-01-01,M,TeamA,1,2,1,06:00,14:00`), 'team');
    expect(data[0].timeRange).toEqual({ start: '06:00', end: '14:00' });
  });

  it('errors on a one-sided override (start without end) and drops timeRange', async () => {
    const { data, errors } = await parseDemandCsv(csvFile(`${HEADER}\n2030-01-01,M,TeamA,1,2,1,06:00,`), 'team');
    expect(errors.join(' ')).toMatch(/set together/);
    expect(data[0].timeRange).toBeUndefined();
  });

  it('errors on a bad HH:MM override time', async () => {
    const { errors } = await parseDemandCsv(csvFile(`${HEADER}\n2030-01-01,M,TeamA,1,2,1,6:00,14:00`), 'team');
    expect(errors.join(' ')).toMatch(/Invalid time format/);
  });

  it('errors when override start >= end', async () => {
    const { errors } = await parseDemandCsv(csvFile(`${HEADER}\n2030-01-01,M,TeamA,1,2,1,16:00,08:00`), 'team');
    expect(errors.join(' ')).toMatch(/start must be before end/);
  });

  it('uses the competency column for the competency model', async () => {
    const { data, errors } = await parseDemandCsv(csvFile('date,workPeriod,competency,minimum,ideal,estimated\n2030-01-01,M,Nurse,1,2,1'), 'competency');
    expect(errors).toEqual([]);
    expect(data[0]).toMatchObject({ competency: 'Nurse' });
  });
});

describe('parseDemandCsvFromText (string, lenient)', () => {
  it('parses valid rows with no per-row validation errors', async () => {
    const { data, errors } = await parseDemandCsvFromText(`${HEADER}\n2030-01-01,M,TeamA,1,2,1,,`, 'team');
    expect(errors).toEqual([]);
    expect(data[0]).toMatchObject({ workPeriod: 'M', minimum: 1 });
  });

  it('does not raise per-row errors for a bad date (lenient)', async () => {
    const { errors } = await parseDemandCsvFromText('date,workPeriod,team,minimum,ideal,estimated\nBADDATE,M,TeamA,1,2,1', 'team');
    expect(errors).toEqual([]);
  });

  it('sets timeRange only for a fully valid override', async () => {
    const { data } = await parseDemandCsvFromText(`${HEADER}\n2030-01-01,M,TeamA,1,2,1,06:00,14:00`, 'team');
    expect(data[0].timeRange).toEqual({ start: '06:00', end: '14:00' });
  });

  it('[characterization] silently drops a one-sided override with no error', async () => {
    const { data, errors } = await parseDemandCsvFromText(`${HEADER}\n2030-01-01,M,TeamA,1,2,1,06:00,`, 'team');
    expect(errors).toEqual([]);
    expect(data[0].timeRange).toBeUndefined();
  });

  it('[characterization] silently ignores an overnight override (start >= end)', async () => {
    const { data } = await parseDemandCsvFromText(`${HEADER}\n2030-01-01,M,TeamA,1,2,1,16:00,08:00`, 'team');
    expect(data[0].timeRange).toBeUndefined();
  });
});
