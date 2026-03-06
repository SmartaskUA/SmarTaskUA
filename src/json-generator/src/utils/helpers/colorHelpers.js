/**
 * Color Helpers
 *
 * Utilities for generating and managing colors for teams/competencies
 */

// Predefined color palette (Material Design inspired)
const COLOR_PALETTE = [
  '#2196F3', // Blue
  '#4CAF50', // Green
  '#FF9800', // Orange
  '#E91E63', // Pink
  '#9C27B0', // Purple
  '#00BCD4', // Cyan
  '#FF5722', // Deep Orange
  '#3F51B5', // Indigo
  '#8BC34A', // Light Green
  '#FFC107', // Amber
  '#673AB7', // Deep Purple
  '#009688', // Teal
  '#795548', // Brown
  '#607D8B', // Blue Grey
  '#F44336', // Red
  '#CDDC39', // Lime
  '#FFEB3B', // Yellow
  '#00897B', // Teal 600
  '#6A1B9A', // Purple 800
  '#1565C0', // Blue 800
];

/**
 * Generate a consistent color for a team/competency
 * Uses hash of the team name to ensure same team always gets same color
 *
 * @param {string} teamName - Team or competency code
 * @returns {string} - Hex color code
 */
export function getTeamColor(teamName) {
  if (!teamName) return COLOR_PALETTE[0];

  // Simple hash function
  let hash = 0;
  for (let i = 0; i < teamName.length; i++) {
    hash = teamName.charCodeAt(i) + ((hash << 5) - hash);
    hash = hash & hash; // Convert to 32bit integer
  }

  // Use hash to select from palette
  const index = Math.abs(hash) % COLOR_PALETTE.length;
  return COLOR_PALETTE[index];
}

/**
 * Generate a color map for all teams
 *
 * @param {Array<string>} teams - Array of team/competency codes
 * @returns {Object} - Map of team code to color
 */
export function generateTeamColorMap(teams) {
  const colorMap = {};
  teams.forEach((team) => {
    const teamCode = typeof team === 'string' ? team : team.code;
    colorMap[teamCode] = getTeamColor(teamCode);
  });
  return colorMap;
}

/**
 * Lighten or darken a color
 *
 * @param {string} color - Hex color code
 * @param {number} amount - Amount to lighten (positive) or darken (negative), -100 to 100
 * @returns {string} - Modified hex color code
 */
export function adjustColor(color, amount) {
  const hex = color.replace('#', '');
  const num = parseInt(hex, 16);

  let r = (num >> 16) + amount;
  let g = ((num >> 8) & 0x00FF) + amount;
  let b = (num & 0x0000FF) + amount;

  r = Math.max(0, Math.min(255, r));
  g = Math.max(0, Math.min(255, g));
  b = Math.max(0, Math.min(255, b));

  return `#${((r << 16) | (g << 8) | b).toString(16).padStart(6, '0')}`;
}

/**
 * Get a lighter version of a color (for hover states)
 *
 * @param {string} color - Hex color code
 * @returns {string} - Lighter hex color code
 */
export function getLighterColor(color) {
  return adjustColor(color, 30);
}

/**
 * Get a darker version of a color (for borders)
 *
 * @param {string} color - Hex color code
 * @returns {string} - Darker hex color code
 */
export function getDarkerColor(color) {
  return adjustColor(color, -30);
}
