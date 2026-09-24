import React, { useRef, useState } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions, Button, TextField, Typography, Box, List, ListItem,
  ListItemText, IconButton, Divider, Alert, Tooltip
} from '@mui/material';
import { Delete, FolderOpen, SaveAlt, Upload, Save, Inventory2 } from '@mui/icons-material';
import { useWizard } from '../../context/WizardContext';
import { isV4State } from '../../v4/persistence';
import BundleImportDialog from '../import/BundleImportDialog';
import { downloadText } from '../../utils/download';

/**
 * Named snapshots of the wizard's state (kept in this browser), a state
 * export/import, and loading a v4.0 bundle. Only v4 states are accepted;
 * v2.x saves are deprecated and are not migrated.
 */
const ProjectManagerDialog = ({ open, onClose }) => {
  const { state, saveProject, deleteProject, loadProject, listProjects } = useWizard();
  const [name, setName] = useState('');
  const [message, setMessage] = useState(null);
  const [projects, setProjects] = useState(() => listProjects());
  const [bundleOpen, setBundleOpen] = useState(false);
  const fileRef = useRef(null);

  const refresh = () => setProjects(listProjects());

  const save = () => {
    if (!name.trim()) return;
    saveProject(name.trim());
    refresh();
    setName('');
    setMessage({ severity: 'success', text: 'Saved.' });
  };

  const importState = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    try {
      const parsed = JSON.parse(await file.text());
      if (!isV4State(parsed)) {
        setMessage({
          severity: 'error',
          text: parsed?.schemaVersion
            ? 'This is a v2.x wizard project. Those are deprecated and cannot be loaded; to start from a problem, import its v4.0 bundle instead.'
            : 'Not a wizard project file. To load problem.json and its CSVs, use "Import v4 bundle".'
        });
        return;
      }
      loadProject(parsed);
      onClose();
    } catch {
      setMessage({ severity: 'error', text: 'Could not parse the file.' });
    }
  };

  return (
    <>
      <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth TransitionProps={{ onEnter: () => { refresh(); setMessage(null); } }}>
        <DialogTitle>Projects</DialogTitle>
        <DialogContent dividers>
          <Typography variant="subtitle2" gutterBottom>Save the current work in this browser</Typography>
          <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
            <TextField size="small" placeholder="Project name" value={name} onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && save()} sx={{ flex: 1 }}
            />
            <Button variant="contained" startIcon={<Save />} onClick={save} disabled={!name.trim()}>Save</Button>
          </Box>

          <Typography variant="subtitle2" gutterBottom>Saved projects</Typography>
          {projects.length === 0 ? (
            <Typography variant="body2" color="text.secondary">None yet.</Typography>
          ) : (
            <List dense>
              {projects.map((p) => (
                <ListItem
                  key={p.name}
                  secondaryAction={(
                    <>
                      <Tooltip title="Load"><IconButton onClick={() => { loadProject(p.state); onClose(); }}><FolderOpen /></IconButton></Tooltip>
                      <Tooltip title="Delete"><IconButton color="error" onClick={() => { deleteProject(p.name); refresh(); }}><Delete /></IconButton></Tooltip>
                    </>
                  )}
                >
                  <ListItemText primary={p.name} secondary={new Date(p.savedAt).toLocaleString()} />
                </ListItem>
              ))}
            </List>
          )}

          <Divider sx={{ my: 2 }} />
          <Typography variant="subtitle2" gutterBottom>Files</Typography>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            <Button variant="outlined" startIcon={<Inventory2 />} onClick={() => setBundleOpen(true)}>Import v4 bundle</Button>
            <Button variant="outlined" startIcon={<SaveAlt />}
              onClick={() => downloadText(`${state.metadata.problemId || 'wizard'}_project.json`, JSON.stringify(state, null, 2), 'application/json')}
            >
              Export project
            </Button>
            <Button variant="outlined" startIcon={<Upload />} onClick={() => fileRef.current?.click()}>Import project</Button>
            <input ref={fileRef} type="file" accept=".json" style={{ display: 'none' }} onChange={importState} />
          </Box>
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
            A project file is the wizard&apos;s own state (weekly template included). A bundle is the v4.0 problem.json and CSVs.
          </Typography>
          {message && <Alert severity={message.severity} sx={{ mt: 2 }}>{message.text}</Alert>}
        </DialogContent>
        <DialogActions><Button onClick={onClose}>Close</Button></DialogActions>
      </Dialog>
      <BundleImportDialog open={bundleOpen} onClose={() => { setBundleOpen(false); onClose(); }} />
    </>
  );
};

export default ProjectManagerDialog;
