import { createTheme } from '@mui/material/styles';
import { themeConfig, typographyConfig, componentOverrides } from './theme.config';

/**
 * Create MUI Theme from configuration
 * Edit theme.config.js to customize colors and typography
 */
export const theme = createTheme({
  palette: {
    mode: 'light',
    primary: themeConfig.primary,
    secondary: themeConfig.secondary,
    success: themeConfig.success,
    warning: themeConfig.warning,
    error: themeConfig.error,
    info: themeConfig.info,
    background: themeConfig.background,
    text: themeConfig.text,
    divider: themeConfig.divider
  },
  typography: typographyConfig,
  components: componentOverrides,
  shape: {
    borderRadius: 8
  },
  spacing: 8
});

export default theme;
