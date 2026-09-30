/**
 * Write bundles the wizard generates to disk and run the canonical Python
 * validator over them — the cross-language check that the JS port can't give.
 *
 *   npx vite-node scripts/validate-with-python.mjs [outDir]
 *
 * Needs python3 (jsonschema optional: without it the Python validator skips
 * only its schema layer and says so). Exits non-zero if any bundle fails.
 */

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { buildBundle, bundleEntries } from '../src/v4/generate';
import { importBundle } from '../src/v4/importBundle';
import { sampleState, sampleStateWithFixedDays } from '../src/v4/fixtures/sampleState';

const here = path.dirname(fileURLToPath(import.meta.url));
const schemaV4 = path.resolve(here, '../../../json_generation/schema_v4');
const outDir = path.resolve(process.argv[2] || fs.mkdtempSync(path.join(os.tmpdir(), 'jsongen-v4-')));

function readDir(dir) {
  return Object.fromEntries(fs.readdirSync(dir)
    .filter((n) => /\.(json|csv)$/.test(n))
    .map((n) => [n, fs.readFileSync(path.join(dir, n), 'utf-8')]));
}

function write(name, state) {
  const dir = path.join(outDir, name);
  fs.mkdirSync(dir, { recursive: true });
  for (const [file, text] of bundleEntries(buildBundle(state))) fs.writeFileSync(path.join(dir, file), text);
  return dir;
}

const regenerate = (example) => importBundle(readDir(path.join(schemaV4, 'examples', example))).state;

const bundles = [
  write('sample', sampleState()),
  write('sample_fixed_days', sampleStateWithFixedDays()),
  write('cenario2_regenerated', regenerate('cenario2_retail')),
  write('cenario2_partial_regenerated', regenerate('cenario2_partial'))
];

let failed = false;
for (const dir of bundles) {
  const run = spawnSync('python3', ['-m', 'schema_v4.validator', dir, '-v'], {
    cwd: schemaV4,
    env: { ...process.env, PYTHONPATH: path.join(schemaV4, 'src'), PYTHONDONTWRITEBYTECODE: '1' },
    encoding: 'utf-8'
  });
  process.stdout.write(`== ${path.relative(outDir, dir)}\n${run.stdout}${run.stderr}`);
  if (run.status !== 0) failed = true;
}
console.log(`bundles written to ${outDir}`);
process.exit(failed ? 1 : 0);
