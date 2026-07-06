import { describe, it, expect } from 'vitest';
import {
  isValidTimeFormat,
  parseTimeToMinutes,
  validateTimeRange,
  parseTimeWindowConstraint,
  validateTimeWindowConstraint,
  isTimeWindowConstraint,
  isTimeConstraint,
  getConstraintType,
  formatTimeWindowConstraint
} from './timeConstraintValidator';

describe('isValidTimeFormat', () => {
  it('accepts valid 24h HH:MM', () => {
    expect(isValidTimeFormat('00:00')).toBe(true);
    expect(isValidTimeFormat('23:59')).toBe(true);
  });
  it('rejects out-of-range, unpadded, or non-string values', () => {
    expect(isValidTimeFormat('24:00')).toBe(false);
    expect(isValidTimeFormat('8:00')).toBe(false);
    expect(isValidTimeFormat('12:60')).toBe(false);
    expect(isValidTimeFormat(800)).toBe(false);
    expect(isValidTimeFormat(null)).toBe(false);
  });
});

describe('parseTimeToMinutes', () => {
  it('converts HH:MM to minutes since midnight', () => {
    expect(parseTimeToMinutes('00:00')).toBe(0);
    expect(parseTimeToMinutes('08:30')).toBe(510);
    expect(parseTimeToMinutes('23:59')).toBe(1439);
  });
});

describe('validateTimeRange', () => {
  it('accepts start < end', () => {
    expect(validateTimeRange('08:00', '16:00')).toEqual({ valid: true });
  });
  it('rejects start >= end', () => {
    expect(validateTimeRange('16:00', '08:00').valid).toBe(false);
    expect(validateTimeRange('08:00', '08:00').valid).toBe(false);
  });
  it('rejects malformed times', () => {
    expect(validateTimeRange('25:00', '26:00').valid).toBe(false);
  });
});

describe('parseTimeWindowConstraint (loose)', () => {
  it('parses each constraint type', () => {
    expect(parseTimeWindowConstraint('EQUALS:08:00-16:00')).toEqual({ type: 'EQUALS', start: '08:00', end: '16:00' });
    expect(parseTimeWindowConstraint('INCLUDE:09:00-12:00')).toMatchObject({ type: 'INCLUDE' });
    expect(parseTimeWindowConstraint('EXCEPT:13:00-14:00')).toMatchObject({ type: 'EXCEPT' });
  });
  it('returns null for non-matching or non-string input', () => {
    expect(parseTimeWindowConstraint('A')).toBeNull();
    expect(parseTimeWindowConstraint('EQUALS:8:00-16:00')).toBeNull(); // needs 2 digits
    expect(parseTimeWindowConstraint(42)).toBeNull();
  });
  it('[characterization] is loose: parses digit-shaped but out-of-range times', () => {
    expect(parseTimeWindowConstraint('EQUALS:99:99-88:88')).toEqual({ type: 'EQUALS', start: '99:99', end: '88:88' });
  });
});

describe('validateTimeWindowConstraint (strict)', () => {
  it('accepts a well-formed, ordered constraint', () => {
    expect(validateTimeWindowConstraint('EQUALS:08:00-16:00')).toMatchObject({ valid: true });
  });
  it('rejects a bad overall format', () => {
    expect(validateTimeWindowConstraint('NOPE').valid).toBe(false);
  });
  it('rejects out-of-range times that the loose parser accepts', () => {
    expect(validateTimeWindowConstraint('EQUALS:99:99-88:88').valid).toBe(false);
    expect(validateTimeWindowConstraint('EQUALS:25:00-26:00').valid).toBe(false);
  });
  it('rejects start >= end', () => {
    expect(validateTimeWindowConstraint('EQUALS:16:00-08:00').valid).toBe(false);
  });
});

describe('isTimeWindowConstraint / isTimeConstraint', () => {
  it('detects the constraint shape and aliases each other', () => {
    expect(isTimeWindowConstraint('INCLUDE:09:00-12:00')).toBe(true);
    expect(isTimeConstraint('INCLUDE:09:00-12:00')).toBe(true);
    expect(isTimeWindowConstraint('A')).toBe(false);
    expect(isTimeWindowConstraint(null)).toBe(false);
  });
  it('[characterization] loose detector returns true for out-of-range digits', () => {
    expect(isTimeWindowConstraint('EQUALS:99:99-88:88')).toBe(true);
  });
});

describe('getConstraintType', () => {
  it('returns the type or null', () => {
    expect(getConstraintType('EXCEPT:13:00-14:00')).toBe('EXCEPT');
    expect(getConstraintType('A')).toBeNull();
  });
});

describe('formatTimeWindowConstraint', () => {
  it('produces human-readable text per type', () => {
    expect(formatTimeWindowConstraint('EQUALS:08:00-16:00')).toMatch(/exactly 08:00 to 16:00/);
    expect(formatTimeWindowConstraint('INCLUDE:09:00-12:00')).toMatch(/cover 09:00 to 12:00/);
    expect(formatTimeWindowConstraint('EXCEPT:13:00-14:00')).toMatch(/Unavailable 13:00 to 14:00/);
  });
  it('returns the input unchanged when unparseable', () => {
    expect(formatTimeWindowConstraint('A')).toBe('A');
  });
});
