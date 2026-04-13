/**
 * Editable Theme Configuration for JSON Generator
 * 
 * Edit colors here to customize the entire application's appearance.
 * Colors are inspired by the main SmarTask frontend for consistency.
 */

export const themeConfig = {
  // Primary Colors
  primary: {
    main: '#007bff',      // Main blue - used for primary buttons, links, active states
    light: '#4da3ff',     // Lighter blue - for hover states
    dark: '#0056b3',      // Darker blue - for pressed states
    contrastText: '#ffffff'
  },

  // Secondary Colors
  secondary: {
    main: '#6c757d',      // Gray - used for secondary buttons and elements
    light: '#9ca3a8',
    dark: '#4e555b',
    contrastText: '#ffffff'
  },

  // Success (Green)
  success: {
    main: '#28a745',      // Green - for success messages, completed states
    light: '#48c261',
    dark: '#1e7e34',
    contrastText: '#ffffff'
  },

  // Warning (Yellow/Orange)
  warning: {
    main: '#FFC107',      // Yellow - for warnings, draft states
    light: '#ffd54f',
    dark: '#c79100',
    contrastText: '#000000'
  },

  // Error (Red)
  error: {
    main: '#F44336',      // Red - for errors, delete actions
    light: '#f6685e',
    dark: '#aa2e25',
    contrastText: '#ffffff'
  },

  // Info (Light Blue)
  info: {
    main: '#2196F3',      // Light blue - for informational elements
    light: '#4dabf5',
    dark: '#1769aa',
    contrastText: '#ffffff'
  },

  // Background Colors
  background: {
    default: '#ffffff',   // Main background
    paper: '#ffffff',     // Card/Paper background
    secondary: '#f8f9fa'  // Alternative background
  },

  // Text Colors
  text: {
    primary: '#213547',   // Main text color
    secondary: '#6c757d', // Secondary text
    disabled: '#9ca3a8',  // Disabled text
    hint: '#9ca3a8'       // Hint text
  },

  // Divider & Borders
  divider: '#dee2e6',

  // Custom Colors for Specific Elements
  custom: {
    // Status indicators
    statusGreen: '#28a745',
    statusOrange: '#fd7e14',
    statusRed: '#dc3545',
    statusBlue: '#007bff',
    
    // Schedule matrix colors
    scheduleAvailable: '#d4edda',    // Light green for available (A)
    scheduleVacation: '#fff3cd',     // Light yellow for vacation
    scheduleOff: '#f8d7da',          // Light red for off days
    scheduleSpecific: '#d1ecf1',     // Light blue for specific hours
    
    // Stepper colors
    stepperActive: '#007bff',
    stepperCompleted: '#28a745',
    stepperInactive: '#dee2e6',
    
    // Sidebar (if needed)
    sidebarBg: '#f8f9fa',
    sidebarActive: '#e9ecef'
  }
};

/**
 * Typography Configuration
 */
export const typographyConfig = {
  fontFamily: [
    'system-ui',
    '-apple-system',
    'BlinkMacSystemFont',
    '"Segoe UI"',
    'Roboto',
    '"Helvetica Neue"',
    'Arial',
    'sans-serif'
  ].join(','),
  
  h1: {
    fontSize: '2.5rem',
    fontWeight: 600,
    lineHeight: 1.2
  },
  h2: {
    fontSize: '2rem',
    fontWeight: 600,
    lineHeight: 1.3
  },
  h3: {
    fontSize: '1.75rem',
    fontWeight: 600,
    lineHeight: 1.4
  },
  h4: {
    fontSize: '1.5rem',
    fontWeight: 500,
    lineHeight: 1.4
  },
  h5: {
    fontSize: '1.25rem',
    fontWeight: 500,
    lineHeight: 1.5
  },
  h6: {
    fontSize: '1rem',
    fontWeight: 500,
    lineHeight: 1.5
  },
  body1: {
    fontSize: '1rem',
    lineHeight: 1.5
  },
  body2: {
    fontSize: '0.875rem',
    lineHeight: 1.43
  },
  button: {
    textTransform: 'none',  // Don't uppercase buttons
    fontWeight: 500
  }
};

/**
 * Component Overrides Configuration
 */
export const componentOverrides = {
  MuiAppBar: {
    styleOverrides: {
      root: {
        borderRadius: 0  // Sharp corners for navigation bar
      }
    }
  },
  MuiButton: {
    styleOverrides: {
      root: {
        borderRadius: '8px',
        padding: '8px 16px',
        fontSize: '14px',
        transition: 'all 0.3s ease'
      }
    }
  },
  MuiTextField: {
    styleOverrides: {
      root: {
        '& .MuiOutlinedInput-root': {
          borderRadius: '5px'
        }
      }
    }
  },
  MuiPaper: {
    styleOverrides: {
      root: {
        borderRadius: '8px'
      }
    }
  },
  MuiCard: {
    styleOverrides: {
      root: {
        borderRadius: '8px',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
      }
    }
  }
};
