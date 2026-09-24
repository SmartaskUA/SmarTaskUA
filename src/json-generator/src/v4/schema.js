/**
 * The JSON Schema layer: problem.json against the vendored schema-v4-input.json.
 *
 * `format` is not asserted, matching the Python validator, whose
 * Draft202012Validator runs without a format_checker. Dates are still checked,
 * because the schema pairs each date format with a pattern.
 */

import Ajv2020 from 'ajv/dist/2020';
import schema from '../../schema_v4/schema-v4-input.json';

const ajv = new Ajv2020({ allErrors: true, strict: false, validateFormats: false });
const validate = ajv.compile(schema);

export { schema };

/** The wizard step that owns each top-level key. */
const STEP_OF_KEY = {
  schemaVersion: 'setup',
  form: 'setup',
  problemType: 'setup',
  metadata: 'setup',
  timeGrid: 'setup',
  temporalScope: 'setup',
  calendar: 'setup',
  contracts: 'contracts',
  employees: 'employees',
  demand: 'demand',
  scheduleInput: 'scheduleInput',
  schedules: 'schedules',
  priorityHierarchy: 'rules',
  constraints: 'rules'
};

function stepOf(segments) {
  if (segments[0] === 'demand' && segments[1] === 'dimensions') return 'dimensions';
  if (!segments.length) return 'review';
  return STEP_OF_KEY[segments[0]] || 'review';
}

function describe(err) {
  switch (err.keyword) {
    case 'required':
      return `'${err.params.missingProperty}' is a required property`;
    case 'additionalProperties':
      return `additional property '${err.params.additionalProperty}' is not allowed`;
    case 'const':
      return `must be ${JSON.stringify(err.params.allowedValue)}`;
    case 'enum':
      return `must be one of ${err.params.allowedValues.map((v) => JSON.stringify(v)).join(', ')}`;
    default:
      return err.message;
  }
}

/** [{message, step}] for every schema violation, sorted by path like the Python validator. */
export function schemaFindings(problem) {
  if (validate(problem)) return [];
  return validate.errors
    // oneOf failures repeat what their branches already said.
    .filter((err) => err.keyword !== 'oneOf')
    .map((err) => {
      const segments = err.instancePath.split('/').filter(Boolean);
      return { segments, message: `schema: ${segments.join('/') || '(root)'}: ${describe(err)}`, step: stepOf(segments) };
    })
    .sort((a, b) => a.segments.join('/').localeCompare(b.segments.join('/')))
    .map(({ message, step }) => ({ message, step }));
}
