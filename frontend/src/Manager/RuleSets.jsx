import React, { useEffect, useState } from "react";
import {
  Box,
  Typography,
  List,
  ListItem,
  ListItemText,
  Button,
  Divider,
  Card,
  CardContent,
  TextField,
  IconButton,
  Stack,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from "@mui/material";
import { Edit, Save, Cancel } from "@mui/icons-material";
import Sidebar_Manager from "../components/Sidebar_Manager";
import axios from "axios";
import BaseUrl from "../components/BaseUrl";

export default function RuleSets() {
  const [ruleSets, setRuleSets] = useState([]);
  const [selectedRuleSet, setSelectedRuleSet] = useState(null);
  const [error, setError] = useState(null);
  const [editingRuleSet, setEditingRuleSet] = useState(null);
  const [editingRule, setEditingRule] = useState(null);
  const [tempValues, setTempValues] = useState({});

  const fetchRuleSets = async () => {
    try {
      const res = await axios.get(`${BaseUrl}/rulesets`);
      setRuleSets(Array.isArray(res.data) ? res.data : []);
      setError(null);
    } catch {
      setError("Failed to fetch rulesets.");
    }
  };

  useEffect(() => {
    fetchRuleSets();
  }, []);

  const handleSelect = (rs) => {
    setSelectedRuleSet(rs);
    setEditingRuleSet(null);
    setEditingRule(null);
    setTempValues({});
  };

  const startEditRuleSet = (rs) => {
    setEditingRuleSet(rs.name);
    setTempValues({ name: rs.name, description: rs.description });
  };

  const saveRuleSet = async () => {
    try {
      await axios.put(`${BaseUrl}/rulesets/${editingRuleSet}`, tempValues);
      fetchRuleSets();
      setEditingRuleSet(null);
    } catch {
      setError("Failed to update ruleset.");
    }
  };

  const startEditRule = (rule, idx) => {
    setEditingRule(idx);
    setTempValues({ ...rule });
  };

  const saveRule = async (idx) => {
    try {
      const updatedRules = [...selectedRuleSet.rules];
      updatedRules[idx] = tempValues;

      // Use the ruleset name for PUT
      await axios.put(`${BaseUrl}/rulesets/${selectedRuleSet.name}`, {
        ...selectedRuleSet,
        rules: updatedRules,
      });

      // Update local state
      setSelectedRuleSet({
        ...selectedRuleSet,
        rules: updatedRules,
      });

      fetchRuleSets();
      setEditingRule(null);
    } catch {
      setError("Failed to update rule.");
    }
  };

  return (
    <div className="admin-container">
      <Sidebar_Manager />
      <Box className="main-content" sx={{ marginRight: 3 }}>
        <Typography variant="h4" gutterBottom>
          Rule Sets
        </Typography>
        {error && <Typography color="error">{error}</Typography>}

        <Box display="flex" gap={4}>
          {/* RuleSets List */}
          <Card sx={{ width: 300, maxHeight: "80vh", overflowY: "auto" }}>
            <List>
              {ruleSets.map((rs) => (
                <React.Fragment key={rs.name}>
                  <ListItem
                    button
                    onClick={() => handleSelect(rs)}
                    sx={{
                      "&:hover": { backgroundColor: "#f5f5f5" },
                      backgroundColor:
                        selectedRuleSet?.name === rs.name ? "#e0f7fa" : "inherit",
                    }}
                  >
                    <ListItemText
                      primary={rs.name}
                      secondary={rs.description}
                    />
                  </ListItem>
                  <Divider />
                </React.Fragment>
              ))}
            </List>
          </Card>

          {/* RuleSet Details */}
          <Box sx={{ flexGrow: 1 }}>
            {selectedRuleSet ? (
              <Card sx={{ padding: 2 }}>
                <CardContent>
                  <Stack direction="row" alignItems="center" spacing={2} mb={2}>
                    {editingRuleSet === selectedRuleSet.name ? (
                      <>
                        <TextField
                          label="Name"
                          value={tempValues.name}
                          onChange={(e) =>
                            setTempValues({ ...tempValues, name: e.target.value })
                          }
                          size="small"
                        />
                        <TextField
                          label="Description"
                          value={tempValues.description}
                          onChange={(e) =>
                            setTempValues({ ...tempValues, description: e.target.value })
                          }
                          size="small"
                        />
                        <IconButton onClick={saveRuleSet} color="primary">
                          <Save />
                        </IconButton>
                        <IconButton
                          onClick={() => setEditingRuleSet(null)}
                          color="error"
                        >
                          <Cancel />
                        </IconButton>
                      </>
                    ) : (
                      <>
                        <Typography variant="h5">{selectedRuleSet.name}</Typography>
                        <IconButton onClick={() => startEditRuleSet(selectedRuleSet)}>
                          <Edit />
                        </IconButton>
                      </>
                    )}
                  </Stack>

                  <Typography variant="subtitle1" gutterBottom>
                    {selectedRuleSet.description}
                  </Typography>

                  <Typography variant="h6" mb={1}>
                    Rules:
                  </Typography>
                  <List>
                    {selectedRuleSet.rules.map((rule, idx) => (
                      <ListItem
                        key={idx}
                        sx={{ flexDirection: "column", alignItems: "flex-start" }}
                      >
                        {editingRule === idx ? (
                          <Stack
                            direction="row"
                            spacing={1}
                            alignItems="center"
                            width="100%"
                          >
                            <TextField
                              label="Type"
                              value={tempValues.type}
                              onChange={(e) =>
                                setTempValues({ ...tempValues, type: e.target.value })
                              }
                              size="small"
                            />

                            <FormControl size="small" sx={{ minWidth: 120 }}>
                              <InputLabel id={`kind-label-${idx}`}>Kind</InputLabel>
                              <Select
                                labelId={`kind-label-${idx}`}
                                value={tempValues.kind}
                                label="Kind"
                                onChange={(e) =>
                                  setTempValues({ ...tempValues, kind: e.target.value })
                                }
                              >
                                <MenuItem value="soft">Soft</MenuItem>
                                <MenuItem value="hard">Hard</MenuItem>
                              </Select>
                            </FormControl>

                            <TextField
                              label="Description"
                              value={tempValues.description}
                              onChange={(e) =>
                                setTempValues({ ...tempValues, description: e.target.value })
                              }
                              fullWidth
                              size="small"
                            />

                            <IconButton onClick={() => saveRule(idx)} color="primary">
                              <Save />
                            </IconButton>
                            <IconButton
                              onClick={() => setEditingRule(null)}
                              color="error"
                            >
                              <Cancel />
                            </IconButton>
                          </Stack>
                        ) : (
                          <Stack
                            direction="row"
                            justifyContent="space-between"
                            width="100%"
                          >
                            <ListItemText
                              primary={`${rule.type} (${rule.kind})`}
                              secondary={rule.description}
                            />
                            <IconButton onClick={() => startEditRule(rule, idx)}>
                              <Edit />
                            </IconButton>
                          </Stack>
                        )}
                      </ListItem>
                    ))}
                  </List>
                </CardContent>
              </Card>
            ) : (
              <Typography>Select a ruleset to see details</Typography>
            )}
          </Box>
        </Box>

        <Box mt={2}>
          <Button variant="contained" onClick={fetchRuleSets}>
            Refresh
          </Button>
        </Box>
      </Box>
    </div>
  );
}
