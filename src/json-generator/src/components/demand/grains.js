/**
 * What each demand grain means, and the note on its three values, shared by
 * the demand dialogs, the row table and the Demand step. Kept out of the .jsx
 * files so each exports only components, for React Fast Refresh.
 */

export const GRAIN_INFO = {
  periods: { title: 'Periods', unit: 'workers', windowed: true, help: 'Headcount wanted in a window.' },
  shifts: { title: 'Shifts', unit: 'workers', windowed: true, help: 'Headcount wanted per window, at the shifts grain.' },
  days: { title: 'Days', unit: 'minutes of work', windowed: false, help: 'Whole-day WORKLOAD in minutes — not headcount.' }
};

export const ORDERING_NOTE = 'minimum, ideal and estimated have no established ordering (agenda item 1): only '
  + 'non-negative is checked, and 0 means unset. Leave ideal and estimated at 0 unless you know what the solver reads.';
