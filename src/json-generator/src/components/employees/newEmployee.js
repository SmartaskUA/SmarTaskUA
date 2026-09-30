/** A blank employee for the form: the first contract, from the start of the horizon. */
export function newEmployee(state) {
  return {
    id: '',
    name: '',
    contractAssignments: [{ contractType: state.contracts.definitions[0]?.id || '', start: state.temporalScope.start || '', end: null }],
    competencyAssignments: []
  };
}
