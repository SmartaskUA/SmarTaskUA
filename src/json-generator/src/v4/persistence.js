/**
 * localStorage persistence for the v4 wizard: the working state and named projects.
 *
 * v2.x saves are deprecated and are not migrated. Their keys are removed on
 * boot, and anything that is not a v4 state is ignored. Every access is
 * guarded, so a corrupt entry or a blocked storage never stops the app loading.
 */

import { STATE_VERSION, withDefaults } from './state';

export const STATE_KEY = 'smartask.jsongen.v4.state';
export const PROJECTS_KEY = 'smartask.jsongen.v4.projects';
export const LEGACY_KEYS = ['wizardState', 'wizardProjects'];

function storageOrNull(storage) {
  try {
    return storage ?? globalThis.localStorage ?? null;
  } catch {
    return null;
  }
}

function readJson(storage, key) {
  try {
    const raw = storage?.getItem(key);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function writeJson(storage, key, value) {
  try {
    storage?.setItem(key, JSON.stringify(value));
    return true;
  } catch {
    return false;
  }
}

export function isV4State(value) {
  return !!value && typeof value === 'object' && value.stateVersion === STATE_VERSION;
}

/** Remove the v2.x wizard's keys. */
export function purgeLegacy(storage) {
  const s = storageOrNull(storage);
  for (const key of LEGACY_KEYS) {
    try {
      s?.removeItem(key);
    } catch {
      // storage blocked: nothing to purge
    }
  }
}

/** The saved working state, or null when there is none or it is not v4. */
export function loadState(storage) {
  const s = storageOrNull(storage);
  purgeLegacy(s);
  const saved = readJson(s, STATE_KEY);
  return isV4State(saved) ? withDefaults(saved) : null;
}

export function saveState(state, storage) {
  return writeJson(storageOrNull(storage), STATE_KEY, state);
}

export function clearState(storage) {
  try {
    storageOrNull(storage)?.removeItem(STATE_KEY);
  } catch {
    // storage blocked
  }
}

/** Saved projects, newest first. Entries that are not v4 are dropped. */
export function listProjects(storage) {
  const projects = readJson(storageOrNull(storage), PROJECTS_KEY);
  if (!Array.isArray(projects)) return [];
  return projects
    .filter((p) => p && typeof p.name === 'string' && isV4State(p.state))
    .sort((a, b) => String(b.savedAt).localeCompare(String(a.savedAt)));
}

export function saveProject(name, state, storage) {
  const s = storageOrNull(storage);
  const projects = listProjects(s).filter((p) => p.name !== name);
  projects.push({ name, savedAt: new Date().toISOString(), state });
  return writeJson(s, PROJECTS_KEY, projects);
}

export function deleteProject(name, storage) {
  const s = storageOrNull(storage);
  return writeJson(s, PROJECTS_KEY, listProjects(s).filter((p) => p.name !== name));
}
