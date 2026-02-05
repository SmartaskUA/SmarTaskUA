import React, { useState, useMemo } from 'react';
import {
  Box,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Chip,
  Typography,
  Alert
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon
} from '@mui/icons-material';
import OrganizationalUnitForm from './OrganizationalUnitForm';

/**
 * OrganizationalUnitTable Component
 *
 * Generic table with CRUD operations for organizational units (teams or competencies).
 * Configurable based on entityType prop.
 */
const OrganizationalUnitTable = ({
  items = [],
  onChange,
  error,
  entityType = 'team' // 'team' or 'competency'
}) => {
  const [openDialog, setOpenDialog] = useState(false);
  const [editingItem, setEditingItem] = useState(null);

  // Configuration based on entity type
  const config = useMemo(() => {
    const isTeam = entityType === 'team';

    return {
      entityName: isTeam ? 'Team' : 'Competency',
      entityNamePlural: isTeam ? 'Teams' : 'Competencies',
      entityNameLower: isTeam ? 'team' : 'competency',
      entityNamePluralLower: isTeam ? 'teams' : 'competencies'
    };
  }, [entityType]);

  const handleAdd = () => {
    setEditingItem(null);
    setOpenDialog(true);
  };

  const handleEdit = (item) => {
    setEditingItem(item);
    setOpenDialog(true);
  };

  const handleDelete = (codeToDelete) => {
    onChange(items.filter(item => item.code !== codeToDelete));
  };

  const handleSave = (itemData) => {
    if (editingItem) {
      // Update existing
      onChange(
        items.map(item =>
          item.code === editingItem.code ? itemData : item
        )
      );
    } else {
      // Add new
      onChange([...items, itemData]);
    }
  };

  const existingCodes = items.map(item => item.code);

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">
          {config.entityNamePlural} ({items.length})
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleAdd}
        >
          Add {config.entityName}
        </Button>
      </Box>

      {/* Error from parent */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* Table */}
      {items.length === 0 ? (
        <Alert severity="info">
          No {config.entityNamePluralLower} defined yet. Click "Add {config.entityName}" to create your first {config.entityNameLower}.
        </Alert>
      ) : (
        <TableContainer component={Paper} variant="outlined">
          <Table stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell>Code</TableCell>
                <TableCell>Name</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {items.map((item) => (
                <TableRow key={item.code} hover>
                  <TableCell>
                    <Chip label={item.code} size="small" color="primary" variant="outlined" />
                  </TableCell>
                  <TableCell>
                    <Typography>{item.name}</Typography>
                  </TableCell>
                  <TableCell align="right">
                    <IconButton
                      size="small"
                      onClick={() => handleEdit(item)}
                      sx={{ mr: 1 }}
                    >
                      <EditIcon />
                    </IconButton>
                    <IconButton
                      size="small"
                      color="error"
                      onClick={() => handleDelete(item.code)}
                    >
                      <DeleteIcon />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Dialog */}
      <OrganizationalUnitForm
        open={openDialog}
        onClose={() => setOpenDialog(false)}
        onSave={handleSave}
        editingItem={editingItem}
        existingCodes={existingCodes}
        entityType={entityType}
      />
    </Box>
  );
};

export default OrganizationalUnitTable;
