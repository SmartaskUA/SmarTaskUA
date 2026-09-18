import { describe, it, expect } from 'vitest';
import {
  getWorkPeriodTimeRange,
  isTimeOverride,
  validateOverrideTime
} from './demandTimeHelpers';

const WPS = [
  { code: 'M', name: 'Morning', timeRange: { start: '08:00', end: '16:00' } },
  { code: 'N', name: 'Night', timeRange: { start: '22:00', end: '06:30' } }, // cross-midnight default
  { code: 'X', name: 'NoTime' } // no timeRange
];

describe('getWorkPeriodTimeRange', () => {
  it('returns the timeRange for a matching code', () => {
    expect(getWorkPeriodTimeRange(WPS, 'M')).toEqual({ start: '08:00', end: '16:00' });
  });
  it('returns null when the code is not found', () => {
    expect(getWorkPeriodTimeRange(WPS, 'ZZ')).toBeNull();
  });
  it('returns null for a work period without a timeRange', () => {
    expect(getWorkPeriodTimeRange(WPS, 'X')).toBeNull();
  });
  it('returns null on empty / missing list', () => {
    expect(getWorkPeriodTimeRange([], 'M')).toBeNull();
    expect(getWorkPeriodTimeRange(undefined, 'M')).toBeNull();
  });
});

describe('isTimeOverride', () => {
  const def = { start: '08:00', end: '16:00' };

  it('is false when timeRange is missing or partial', () => {
    expect(isTimeOverride(undefined, def)).toBe(false);
    expect(isTimeOverride({ start: '08:00' }, def)).toBe(false);
    expect(isTimeOverride({ start: '', end: '' }, def)).toBe(false);
  });
  it('is false when there is no known default to compare against', () => {
    expect(isTimeOverride({ start: '08:00', end: '16:00' }, null)).toBe(false);
  });
  it('is false when the time equals the default', () => {
    expect(isTimeOverride({ start: '08:00', end: '16:00' }, def)).toBe(false);
  });
  it('is true when either start or end differs', () => {
    expect(isTimeOverride({ start: '09:00', end: '16:00' }, def)).toBe(true);
    expect(isTimeOverride({ start: '08:00', end: '17:00' }, def)).toBe(true);
  });
});

describe('validateOverrideTime', () => {
  const def = { start: '08:00', end: '16:00' };

  it('returns null when the time is not an override', () => {
    expect(validateOverrideTime({ start: '08:00', end: '16:00' }, def)).toBeNull();
    expect(validateOverrideTime(undefined, def)).toBeNull();
  });
  it('returns null for a valid same-day override', () => {
    expect(validateOverrideTime({ start: '06:00', end: '14:00' }, def)).toBeNull();
  });
  it('rejects a badly formatted override time', () => {
    expect(validateOverrideTime({ start: '6:00', end: '14:00' }, def)).toMatch(/HH:MM/);
  });
  it('rejects an overnight (start >= end) override', () => {
    expect(validateOverrideTime({ start: '16:00', end: '08:00' }, def)).toMatch(/start must be before end/);
  });
  it('allows a cross-midnight work-period default when left unchanged (not an override)', () => {
    const nightDef = { start: '22:00', end: '06:30' };
    expect(validateOverrideTime({ start: '22:00', end: '06:30' }, nightDef)).toBeNull();
  });
});
