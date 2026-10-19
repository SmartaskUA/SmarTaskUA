// @vitest-environment node
import { describe, it, expect, beforeEach } from 'vitest';
import * as persistence from './persistence';
import { createInitialState } from './state';

function memoryStorage(initial = {}) {
  const data = { ...initial };
  return {
    data,
    getItem: (k) => (k in data ? data[k] : null),
    setItem: (k, v) => { data[k] = String(v); },
    removeItem: (k) => { delete data[k]; }
  };
}

describe('persistence', () => {
  let storage;
  beforeEach(() => { storage = memoryStorage(); });

  it('purges the v2.x keys on load and ignores them', () => {
    storage = memoryStorage({
      wizardState: JSON.stringify({ schemaVersion: '2.2', employees: { model: 'team' } }),
      wizardProjects: '[]'
    });
    expect(persistence.loadState(storage)).toBeNull();
    expect(storage.data).toEqual({});
  });

  it('round-trips a v4 state', () => {
    const state = createInitialState();
    state.metadata.problemId = 'C2_January_2026';
    persistence.saveState(state, storage);
    expect(persistence.loadState(storage).metadata.problemId).toBe('C2_January_2026');
  });

  it('ignores a state that is not v4, and survives a corrupt entry', () => {
    storage.setItem(persistence.STATE_KEY, JSON.stringify({ schemaVersion: '2.6' }));
    expect(persistence.loadState(storage)).toBeNull();
    storage.setItem(persistence.STATE_KEY, '{not json');
    expect(persistence.loadState(storage)).toBeNull();
  });

  it('fills keys a saved state is missing', () => {
    const partial = createInitialState();
    delete partial.schedules;
    storage.setItem(persistence.STATE_KEY, JSON.stringify(partial));
    expect(persistence.loadState(storage).schedules.rows).toHaveLength(3);
  });

  it('keeps v4 projects only, newest first, replacing by name', () => {
    storage.setItem(persistence.PROJECTS_KEY, JSON.stringify([
      { name: 'old', savedAt: '2025-01-01', state: { schemaVersion: '2.2' } }
    ]));
    persistence.saveProject('a', createInitialState(), storage);
    persistence.saveProject('b', createInitialState(), storage);
    persistence.saveProject('a', createInitialState(), storage);
    expect(persistence.listProjects(storage).map((p) => p.name)).toEqual(['a', 'b']);
    persistence.deleteProject('a', storage);
    expect(persistence.listProjects(storage).map((p) => p.name)).toEqual(['b']);
  });

  it('never throws when storage is blocked', () => {
    const blocked = {
      getItem: () => { throw new Error('denied'); },
      setItem: () => { throw new Error('denied'); },
      removeItem: () => { throw new Error('denied'); }
    };
    expect(persistence.loadState(blocked)).toBeNull();
    expect(persistence.saveState(createInitialState(), blocked)).toBe(false);
    expect(persistence.listProjects(blocked)).toEqual([]);
  });
});
