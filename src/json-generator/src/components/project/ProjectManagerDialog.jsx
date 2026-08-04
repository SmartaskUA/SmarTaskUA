import React, { useState, useRef } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions,
  Button, TextField, Typography, Box, List, ListItem,
  ListItemText, ListItemSecondaryAction, IconButton, Divider,
  Alert, Tooltip
} from '@mui/material';
import { Delete, FolderOpen, SaveAlt, Upload, Save } from '@mui/icons-material';
import { saveAs } from 'file-saver';
import { useWizard } from '../../context/WizardContext';

const ProjectManagerDialog = ({ open, onClose }) => {
  const { state, saveProject, deleteProject, loadProject } = useWizard();
  const [saveName, setSaveName] = useState('');
  const [saveError, setSaveError] = useState('');
  const [importError, setImportError] = useState('');
  const [saved, setSaved] = useState(false);
  const fileInputRef = useRef(null);

  const getSavedProjects = () => {
    try {
      return JSON.parse(localStorage.getItem('wizardProjects') || '[]');
    } catch {
      return [];
    }
  };

  const [projects, setProjects] = useState(getSavedProjects);

  const refreshProjects = () => setProjects(getSavedProjects());

  const handleSave = () => {
    const name = saveName.trim();
    if (!name) {
      setSaveError('Enter a project name.');
      return;
    }
    saveProject(name);
    refreshProjects();
    setSaveName('');
    setSaveError('');
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleDelete = (name) => {
    deleteProject(name);
    refreshProjects();
  };

  const handleLoad = (project) => {
    loadProject(project.state);
    onClose();
  };

  const handleExport = () => {
    const name = state.metadata?.problemId || 'wizard_state';
    const blob = new Blob([JSON.stringify(state, null, 2)], { type: 'application/json' });
    saveAs(blob, `${name}_project.json`);
  };

  const handleImportClick = () => {
    setImportError('');
    fileInputRef.current?.click();
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (evt) => {
      try {
        const parsed = JSON.parse(evt.target.result);
        if (typeof parsed !== 'object' || !parsed.schemaVersion) {
          setImportError('Invalid project file — missing schemaVersion.');
          return;
        }
        loadProject(parsed);
        onClose();
      } catch {
        setImportError('Could not parse file. Make sure it is a valid project JSON.');
      }
    };
    reader.readAsText(file);
    e.target.value = '';
  };

  const formatDate = (iso) => {
    try {
      return new Date(iso).toLocaleString();
    } catch {
      return iso;
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Project Manager</DialogTitle>

      <DialogContent dividers>
        {/* Save current state */}
        <Typography variant="subtitle2" gutterBottom>Save current state</Typography>
        <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
          <TextField
            size="small"
            placeholder="Project name"
            value={saveName}
            onChange={e => { setSaveName(e.target.value); setSaveError(''); }}
            onKeyDown={e => e.key === 'Enter' && handleSave()}
            error={!!saveError}
            helperText={saveError}
            sx={{ flex: 1 }}
          />
          <Button
            variant="contained"
            startIcon={<Save />}
            onClick={handleSave}
            disabled={!saveName.trim()}
          >
            Save
          </Button>
        </Box>
        {saved && <Alert severity="success" sx={{ mb: 1 }}>Saved!</Alert>}

        <Divider sx={{ my: 2 }} />

        {/* Saved projects list */}
        <Typography variant="subtitle2" gutterBottom>
          Saved projects {projects.length > 0 ? `(${projects.length})` : ''}
        </Typography>

        {projects.length === 0 ? (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            No saved projects yet.
          </Typography>
        ) : (
          <List dense disablePadding sx={{ mb: 1 }}>
            {projects.map((p) => (
              <ListItem key={p.name} sx={{ pl: 0, pr: 10 }}>
                <ListItemText
                  primary={p.name}
                  secondary={formatDate(p.savedAt)}
                  primaryTypographyProps={{ fontWeight: 500 }}
                />
                <ListItemSecondaryAction>
                  <Tooltip title="Load">
                    <IconButton size="small" onClick={() => handleLoad(p)} sx={{ mr: 0.5 }}>
                      <FolderOpen fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Delete">
                    <IconButton size="small" color="error" onClick={() => handleDelete(p.name)}>
                      <Delete fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </ListItemSecondaryAction>
              </ListItem>
            ))}
          </List>
        )}

        <Divider sx={{ my: 2 }} />

        {/* Export / Import */}
        <Typography variant="subtitle2" gutterBottom>Export / Import</Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={<SaveAlt />}
            onClick={handleExport}
            size="small"
          >
            Export to file
          </Button>
          <Button
            variant="outlined"
            startIcon={<Upload />}
            onClick={handleImportClick}
            size="small"
          >
            Import from file
          </Button>
        </Box>
        {importError && <Alert severity="error" sx={{ mt: 1 }}>{importError}</Alert>}

        <input
          ref={fileInputRef}
          type="file"
          accept=".json"
          style={{ display: 'none' }}
          onChange={handleFileChange}
        />
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
};

export default ProjectManagerDialog;
