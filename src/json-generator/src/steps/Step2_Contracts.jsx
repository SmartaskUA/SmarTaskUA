import React, { useState } from 'react';
import {
  Box,
  Typography,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Chip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Checkbox,
  FormControlLabel,
  FormGroup,
  Grid,
  Alert
} from '@mui/material';
import {
  Add,
  Edit,
  Delete,
  ExpandMore
} from '@mui/icons-material';
import StepCard from '../components/wizard/StepCard';
import NavigationButtons from '../components/wizard/NavigationButtons';
import { useWizard } from '../context/WizardContext';

/**
 * Step 2: Contracts
 * 
 * Define reusable contract types with:
 * - ID, Name, Work Hours Per Day
 * - Optional constraints (weekends only, max hours, etc.)
 */
const Step2_Contracts = () => {
  const { state, updateState } = useWizard();
  const contracts = state.contracts.definitions;

  const [openDialog, setOpenDialog] = useState(false);
  const [editingContract, setEditingContract] = useState(null);
  const [errors, setErrors] = useState({});

  // Form state
  const [formData, setFormData] = useState({
    id: '',
    name: '',
    workHoursPerDay: 8,
    constraints: {
      weekendsOnly: false,
      weekdaysOnly: false,
      availableDays: [],
      maxHoursPerWeek: '',
      maxConsecutiveDays: '',
      minRestDaysPerWeek: '',
      flexibleHours: false
    }
  });

  const handleAddContract = () => {
    setEditingContract(null);
    setFormData({
      id: '',
      name: '',
      workHoursPerDay: 8,
      constraints: {
        weekendsOnly: false,
        weekdaysOnly: false,
        availableDays: [],
        maxHoursPerWeek: '',
        maxConsecutiveDays: '',
        minRestDaysPerWeek: '',
        flexibleHours: false
      }
    });
    setErrors({});
    setOpenDialog(true);
  };

  const handleEditContract = (contract) => {
    setEditingContract(contract);
    setFormData(contract);
    setErrors({});
    setOpenDialog(true);
  };

  const handleDeleteContract = (contractId) => {
    const newContracts = contracts.filter(c => c.id !== contractId);
    updateState('contracts.definitions', newContracts);
  };

  const handleSaveContract = () => {
    // Validation
    const newErrors = {};
    
    if (!formData.id.trim()) {
      newErrors.id = 'Contract ID is required';
    } else if (
      !editingContract && 
      contracts.some(c => c.id === formData.id)
    ) {
      newErrors.id = 'Contract ID must be unique';
    }

    if (!formData.name.trim()) {
      newErrors.name = 'Contract name is required';
    }

    if (formData.workHoursPerDay < 0 || formData.workHoursPerDay > 24) {
      newErrors.workHoursPerDay = 'Work hours must be between 0 and 24';
    }

    if (formData.constraints.weekendsOnly && formData.constraints.weekdaysOnly) {
      newErrors.constraints = 'Weekends Only and Weekdays Only are mutually exclusive';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    // Clean up constraints - remove empty fields
    const cleanedConstraints = {};
    const { constraints } = formData;
    
    if (constraints.weekendsOnly) cleanedConstraints.weekendsOnly = true;
    if (constraints.weekdaysOnly) cleanedConstraints.weekdaysOnly = true;
    if (constraints.availableDays?.length > 0) cleanedConstraints.availableDays = constraints.availableDays;
    if (constraints.maxHoursPerWeek) cleanedConstraints.maxHoursPerWeek = parseFloat(constraints.maxHoursPerWeek);
    if (constraints.maxConsecutiveDays) cleanedConstraints.maxConsecutiveDays = parseInt(constraints.maxConsecutiveDays);
    if (constraints.minRestDaysPerWeek) cleanedConstraints.minRestDaysPerWeek = parseInt(constraints.minRestDaysPerWeek);
    if (constraints.flexibleHours) cleanedConstraints.flexibleHours = true;

    const contractData = {
      id: formData.id,
      name: formData.name,
      workHoursPerDay: parseFloat(formData.workHoursPerDay),
      ...(Object.keys(cleanedConstraints).length > 0 && { constraints: cleanedConstraints })
    };

    let newContracts;
    if (editingContract) {
      // Update existing
      newContracts = contracts.map(c => 
        c.id === editingContract.id ? contractData : c
      );
    } else {
      // Add new
      newContracts = [...contracts, contractData];
    }

    updateState('contracts.definitions', newContracts);
    setOpenDialog(false);
  };

  const handleFormChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: null }));
    }
  };

  const handleConstraintChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      constraints: {
        ...prev.constraints,
        [field]: value
      }
    }));
    if (errors.constraints) {
      setErrors(prev => ({ ...prev, constraints: null }));
    }
  };

  const validate = () => {
    if (contracts.length === 0) {
      return 'At least one contract is required';
    }
    return null;
  };

  const handleNext = () => {
    const error = validate();
    if (error) {
      return false;
    }
    return true;
  };

  const weekDays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];

  return (
    <Box>
      <Typography variant="h4" gutterBottom fontWeight={600}>
        Contract Definitions
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph>
        Define reusable contract types for your employees. Each contract specifies work hours and optional constraints.
      </Typography>

      <StepCard>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">Contracts ({contracts.length})</Typography>
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={handleAddContract}
          >
            Add Contract
          </Button>
        </Box>

        {contracts.length === 0 ? (
          <Alert severity="info">
            No contracts defined yet. Click "Add Contract" to create your first contract type.
          </Alert>
        ) : (
          <TableContainer component={Paper} variant="outlined">
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>ID</TableCell>
                  <TableCell>Name</TableCell>
                  <TableCell align="center">Work Hours/Day</TableCell>
                  <TableCell>Constraints</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {contracts.map((contract) => (
                  <TableRow key={contract.id}>
                    <TableCell>
                      <Chip label={contract.id} size="small" />
                    </TableCell>
                    <TableCell>{contract.name}</TableCell>
                    <TableCell align="center">
                      <Typography fontWeight={600}>{contract.workHoursPerDay}h</Typography>
                    </TableCell>
                    <TableCell>
                      {contract.constraints ? (
                        <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                          {contract.constraints.weekendsOnly && <Chip label="Weekends Only" size="small" color="info" />}
                          {contract.constraints.weekdaysOnly && <Chip label="Weekdays Only" size="small" color="info" />}
                          {contract.constraints.maxHoursPerWeek && <Chip label={`Max ${contract.constraints.maxHoursPerWeek}h/week`} size="small" />}
                          {contract.constraints.maxConsecutiveDays && <Chip label={`Max ${contract.constraints.maxConsecutiveDays} consec.`} size="small" />}
                          {contract.constraints.minRestDaysPerWeek && <Chip label={`${contract.constraints.minRestDaysPerWeek} rest days/week`} size="small" />}
                          {contract.constraints.flexibleHours && <Chip label="Flexible" size="small" color="success" />}
                        </Box>
                      ) : (
                        <Typography variant="body2" color="text.secondary">None</Typography>
                      )}
                    </TableCell>
                    <TableCell align="right">
                      <IconButton size="small" onClick={() => handleEditContract(contract)}>
                        <Edit />
                      </IconButton>
                      <IconButton size="small" color="error" onClick={() => handleDeleteContract(contract.id)}>
                        <Delete />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </StepCard>

      {/* Add/Edit Contract Dialog */}
      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          {editingContract ? 'Edit Contract' : 'Add New Contract'}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Contract ID"
                  value={formData.id}
                  onChange={(e) => handleFormChange('id', e.target.value)}
                  error={!!errors.id}
                  helperText={errors.id || 'e.g., fullTime_8h, partTime_4h'}
                  required
                  disabled={!!editingContract}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Contract Name"
                  value={formData.name}
                  onChange={(e) => handleFormChange('name', e.target.value)}
                  error={!!errors.name}
                  helperText={errors.name || 'Human-readable name'}
                  required
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  type="number"
                  label="Work Hours Per Day"
                  value={formData.workHoursPerDay}
                  onChange={(e) => handleFormChange('workHoursPerDay', e.target.value)}
                  error={!!errors.workHoursPerDay}
                  helperText={errors.workHoursPerDay || 'Default hours when "A" is used in schedule (0-24)'}
                  required
                  inputProps={{ min: 0, max: 24, step: 0.5 }}
                />
              </Grid>

              {/* Optional Constraints */}
              <Grid item xs={12}>
                <Accordion>
                  <AccordionSummary expandIcon={<ExpandMore />}>
                    <Typography>Optional Constraints</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <FormGroup>
                      {errors.constraints && (
                        <Alert severity="error" sx={{ mb: 2 }}>{errors.constraints}</Alert>
                      )}
                      
                      <FormControlLabel
                        control={
                          <Checkbox
                            checked={formData.constraints.weekendsOnly}
                            onChange={(e) => handleConstraintChange('weekendsOnly', e.target.checked)}
                          />
                        }
                        label="Weekends Only (Saturday & Sunday)"
                      />
                      <FormControlLabel
                        control={
                          <Checkbox
                            checked={formData.constraints.weekdaysOnly}
                            onChange={(e) => handleConstraintChange('weekdaysOnly', e.target.checked)}
                          />
                        }
                        label="Weekdays Only (Monday-Friday)"
                      />
                      <FormControlLabel
                        control={
                          <Checkbox
                            checked={formData.constraints.flexibleHours}
                            onChange={(e) => handleConstraintChange('flexibleHours', e.target.checked)}
                          />
                        }
                        label="Flexible Hours"
                      />

                      <Box sx={{ mt: 2 }}>
                        <TextField
                          fullWidth
                          type="number"
                          label="Max Hours Per Week"
                          value={formData.constraints.maxHoursPerWeek}
                          onChange={(e) => handleConstraintChange('maxHoursPerWeek', e.target.value)}
                          helperText="Leave empty for no limit"
                          size="small"
                          inputProps={{ min: 0 }}
                          sx={{ mb: 2 }}
                        />
                        <TextField
                          fullWidth
                          type="number"
                          label="Max Consecutive Days"
                          value={formData.constraints.maxConsecutiveDays}
                          onChange={(e) => handleConstraintChange('maxConsecutiveDays', e.target.value)}
                          helperText="Maximum consecutive work days"
                          size="small"
                          inputProps={{ min: 1 }}
                          sx={{ mb: 2 }}
                        />
                        <TextField
                          fullWidth
                          type="number"
                          label="Min Rest Days Per Week"
                          value={formData.constraints.minRestDaysPerWeek}
                          onChange={(e) => handleConstraintChange('minRestDaysPerWeek', e.target.value)}
                          helperText="Minimum rest days required per week"
                          size="small"
                          inputProps={{ min: 0, max: 7 }}
                        />
                      </Box>
                    </FormGroup>
                  </AccordionDetails>
                </Accordion>
              </Grid>
            </Grid>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleSaveContract}>
            {editingContract ? 'Update' : 'Add'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Navigation */}
      <NavigationButtons 
        onNext={handleNext}
        nextDisabled={contracts.length === 0}
      />
    </Box>
  );
};

export default Step2_Contracts;
