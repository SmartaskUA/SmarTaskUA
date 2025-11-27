import React, { useEffect, useMemo, useState } from "react";
import {
  Box,
  Typography,
  List,
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
  Alert,
  Collapse,
  Avatar,
  Chip,
  Skeleton,
  InputAdornment,
  ListItemButton,
  ListItemAvatar,
} from "@mui/material";
import { Edit, Save, Cancel, Search as SearchIcon, Sort as SortIcon } from "@mui/icons-material";
import Sidebar_Manager from "../components/Sidebar_Manager";
import axios from "axios";
import BaseUrl from "../components/BaseUrl";
import CreateRuleSet from "./CreateRuleSet";

function getInitials(name = "") {
  const parts = name.trim().split(/\s+/).slice(0, 2);
  return parts.map(p => p[0]?.toUpperCase() ?? "").join("");
}

function formatDate(dt) {
  if (!dt) return "";
  try {
    const d = new Date(dt);
    if (Number.isNaN(d.getTime())) return "";
    return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "2-digit" });
  } catch {
    return "";
  }
}

export default function RuleSets() {
  const [ruleSets, setRuleSets] = useState([]);
  const [selectedRuleSet, setSelectedRuleSet] = useState(null);
  const [error, setError] = useState(null);
  const [editingRuleSet, setEditingRuleSet] = useState(null);
  const [editingRule, setEditingRule] = useState(null);
  const [tempValues, setTempValues] = useState({});
  const [paramsError, setParamsError] = useState(null);
  const [createOpen, setCreateOpen] = useState(false);

  // New UI state for the list
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState("updated_desc"); // "updated_desc" | "name_asc" | "name_desc" | "rules_desc"

  const existingNames = (ruleSets || []).map((r) => r.name);

  const fetchRuleSets = async () => {
    try {
      setLoading(true);
      const res = await axios.get(`${BaseUrl}/rulesets`);
      setRuleSets(Array.isArray(res.data) ? res.data : []);
      setError(null);
    } catch {
      setError("Failed to fetch rulesets.");
    } finally {
      setLoading(false);
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
    setParamsError(null);
  };

  const startEditRuleSet = (rs) => {
    setEditingRuleSet(rs.name);
    setTempValues({ name: rs.name, description: rs.description });
  };

  const saveRuleSet = async () => {
    try {
      await axios.put(`${BaseUrl}/rulesets/${editingRuleSet}`, {
        name: tempValues.name,
        description: tempValues.description,
      });
      await fetchRuleSets();
      setEditingRuleSet(null);
    } catch {
      setError("Failed to update ruleset.");
    }
  };

  const startEditRule = (rule, idx) => {
    setEditingRule(idx);
    setParamsError(null);
    setTempValues({
      ...rule,
      paramsJson: JSON.stringify(rule?.params ?? {}, null, 2),
    });
  };

  const parseParamsOrError = (jsonStr) => {
    try {
      const parsed = jsonStr && jsonStr.trim() ? JSON.parse(jsonStr) : {};
      setParamsError(null);
      return parsed;
    } catch (e) {
      setParamsError(e?.message || "Invalid JSON in params.");
      return null;
    }
  };

  const saveRule = async (idx) => {
    const parsedParams = parseParamsOrError(tempValues.paramsJson ?? "");
    if (parsedParams === null) return;

    try {
      const updatedRules = [...(selectedRuleSet?.rules || [])];
      const toSave = {
        ...tempValues,
        params: parsedParams,
      };
      delete toSave.paramsJson;

      updatedRules[idx] = toSave;

      await axios.put(`${BaseUrl}/rulesets/${selectedRuleSet.name}`, {
        ...selectedRuleSet,
        rules: updatedRules,
      });

      setSelectedRuleSet({
        ...selectedRuleSet,
        rules: updatedRules,
      });

      await fetchRuleSets();
      setEditingRule(null);
      setParamsError(null);
    } catch {
      setError("Failed to update rule.");
    }
  };

  // Filter + sort list for prettier sidebar
  const filteredSortedRuleSets = useMemo(() => {
    const term = search.trim().toLowerCase();
    let list = ruleSets;
    if (term) {
      list = list.filter(
        (rs) =>
          rs.name?.toLowerCase().includes(term) ||
          rs.description?.toLowerCase().includes(term)
      );
    }
    const safeRulesCount = (rs) => (Array.isArray(rs.rules) ? rs.rules.length : 0);
    return [...list].sort((a, b) => {
      if (sortBy === "name_asc") return a.name.localeCompare(b.name);
      if (sortBy === "name_desc") return b.name.localeCompare(a.name);
      if (sortBy === "rules_desc") return safeRulesCount(b) - safeRulesCount(a);
      // default updated_desc
      const ua = new Date(a.updatedAt || a.createdAt || 0).getTime();
      const ub = new Date(b.updatedAt || b.createdAt || 0).getTime();
      return ub - ua;
    });
  }, [ruleSets, search, sortBy]);

  return (
    <div className="admin-container">
      <Sidebar_Manager />
      <Box className="main-content" sx={{ marginRight: 3 }}>
        <Stack direction="row" alignItems="center" justifyContent="space-between" mb={1}>
          <Typography variant="h4">Rule Sets</Typography>
          <Button variant="contained" onClick={() => setCreateOpen(true)}>
            New Rule Set
          </Button>
        </Stack>

        <Collapse in={!!error}>
          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
        </Collapse>

        <Box display="flex" gap={4}>
          {/* Prettier RuleSets List */}
          <Card sx={{ width: 500, maxHeight: "80vh", display: "flex", flexDirection: "column" }}>
            <CardContent sx={{ pb: 1 }}>
              <Stack spacing={1.5}>
                <TextField
                  size="small"
                  placeholder="Search rule sets…"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <SearchIcon fontSize="small" />
                      </InputAdornment>
                    ),
                  }}
                />
                <Stack direction="row" alignItems="center" justifyContent="space-between">
                  <FormControl size="small" sx={{ minWidth: 160 }}>
                    <InputLabel id="sort-rs">Sort by</InputLabel>
                    <Select
                      labelId="sort-rs"
                      value={sortBy}
                      label="Sort by"
                      onChange={(e) => setSortBy(e.target.value)}
                      startAdornment={
                        <InputAdornment position="start">
                          <SortIcon fontSize="small" />
                        </InputAdornment>
                      }
                    >
                      <MenuItem value="updated_desc">Recently updated</MenuItem>
                      <MenuItem value="name_asc">Name (A–Z)</MenuItem>
                      <MenuItem value="name_desc">Name (Z–A)</MenuItem>
                      <MenuItem value="rules_desc">Rules (most)</MenuItem>
                    </Select>
                  </FormControl>
                  <Chip
                    label={`${filteredSortedRuleSets.length} total`}
                    size="small"
                    variant="outlined"
                  />
                </Stack>
              </Stack>
            </CardContent>

            <Divider />

            <Box sx={{ overflowY: "auto", px: 1 }}>
              {loading ? (
                <List dense disablePadding sx={{ py: 1 }}>
                  {Array.from({ length: 6 }).map((_, i) => (
                    <Box key={i}>
                      <ListItemButton sx={{ borderRadius: 1, mb: 0.5 }}>
                        <ListItemAvatar>
                          <Skeleton variant="circular" width={32} height={32} />
                        </ListItemAvatar>
                        <ListItemText
                          primary={<Skeleton width="60%" />}
                          secondary={<Skeleton width="40%" />}
                        />
                        <Skeleton variant="rounded" width={48} height={20} />
                      </ListItemButton>
                    </Box>
                  ))}
                </List>
              ) : filteredSortedRuleSets.length === 0 ? (
                <Box sx={{ p: 2.5, textAlign: "center", color: "text.secondary" }}>
                  <Typography variant="body2">No rule sets found.</Typography>
                  <Typography variant="caption">
                    Try adjusting your search or create a new one.
                  </Typography>
                </Box>
              ) : (
                <List dense disablePadding sx={{ py: 1 }}>
                  {filteredSortedRuleSets.map((rs) => {
                    const selected = selectedRuleSet?.name === rs.name;
                    const rulesCount = Array.isArray(rs.rules) ? rs.rules.length : 0;
                    return (
                      <Box key={rs.name}>
                        <ListItemButton
                          onClick={() => handleSelect(rs)}
                          selected={selected}
                          sx={{
                            borderRadius: 1,
                            mb: 0.5,
                            "&.Mui-selected": {
                              bgcolor: "primary.50",
                            },
                            "&:hover": {
                              bgcolor: selected ? "primary.50" : "action.hover",
                            },
                          }}
                        >
                          <ListItemAvatar>
                            <Avatar sx={{ width: 32, height: 32 }}>
                              {getInitials(rs.name)}
                            </Avatar>
                          </ListItemAvatar>
                          <ListItemText
                            primary={
                              <Typography variant="subtitle1" noWrap>
                                {rs.name}
                              </Typography>
                            }
                            secondary={
                              <Typography
                                variant="body2"
                                color="text.secondary"
                                noWrap
                                title={rs.description}
                              >
                                {rs.description || "—"}
                              </Typography>
                            }
                          />
                          <Stack alignItems="flex-end" spacing={0.5}>
                            <Chip
                              size="small"
                              label={`${rulesCount} rule${rulesCount === 1 ? "" : "s"}`}
                              variant="outlined"
                            />
                            <Typography variant="caption" color="text.secondary">
                              {formatDate(rs.updatedAt || rs.createdAt)}
                            </Typography>
                          </Stack>
                        </ListItemButton>
                      </Box>
                    );
                  })}
                </List>
              )}
            </Box>
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
                          value={tempValues.name ?? ""}
                          onChange={(e) =>
                            setTempValues({ ...tempValues, name: e.target.value })
                          }
                          size="small"
                        />
                        <TextField
                          label="Description"
                          value={tempValues.description ?? ""}
                          onChange={(e) =>
                            setTempValues({
                              ...tempValues,
                              description: e.target.value,
                            })
                          }
                          size="small"
                          sx={{ minWidth: 360 }}
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
                    {(selectedRuleSet.rules || []).map((rule, idx) => (
                      <Box
                        key={idx}
                        component="li"
                        sx={{ listStyle: "none", mb: 1 }}
                      >
                        {editingRule === idx ? (
                          <Stack spacing={1} width="100%">
                            <Stack
                              direction={{ xs: "column", sm: "row" }}
                              spacing={1}
                              alignItems={{ xs: "stretch", sm: "center" }}
                            >
                              <TextField
                                label="Type"
                                value={tempValues.type ?? ""}
                                onChange={(e) =>
                                  setTempValues({
                                    ...tempValues,
                                    type: e.target.value,
                                  })
                                }
                                size="small"
                                sx={{ minWidth: 180 }}
                              />

                              <FormControl size="small" sx={{ minWidth: 140 }}>
                                <InputLabel id={`kind-label-${idx}`}>Kind</InputLabel>
                                <Select
                                  labelId={`kind-label-${idx}`}
                                  value={tempValues.kind ?? ""}
                                  label="Kind"
                                  onChange={(e) =>
                                    setTempValues({
                                      ...tempValues,
                                      kind: e.target.value,
                                    })
                                  }
                                >
                                  <MenuItem value="soft">Soft</MenuItem>
                                  <MenuItem value="hard">Hard</MenuItem>
                                </Select>
                              </FormControl>

                              <TextField
                                label="Description"
                                value={tempValues.description ?? ""}
                                onChange={(e) =>
                                  setTempValues({
                                    ...tempValues,
                                    description: e.target.value,
                                  })
                                }
                                fullWidth
                                size="small"
                              />
                            </Stack>

                            <TextField
                              label="Params (JSON)"
                              value={tempValues.paramsJson ?? ""}
                              onChange={(e) => {
                                const val = e.target.value;
                                setTempValues({
                                  ...tempValues,
                                  paramsJson: val,
                                });
                                try {
                                  JSON.parse(val || "{}");
                                  setParamsError(null);
                                } catch (err) {
                                  setParamsError(err?.message || "Invalid JSON");
                                }
                              }}
                              multiline
                              minRows={6}
                              maxRows={16}
                              placeholder={`e.g. {\n  "threshold": 0.8,\n  "enabled": true\n}`}
                              sx={{ fontFamily: "monospace" }}
                            />

                            <Collapse in={!!paramsError}>
                              {paramsError && (
                                <Alert severity="error">{paramsError}</Alert>
                              )}
                            </Collapse>

                            <Stack direction="row" spacing={1} justifyContent="flex-end">
                              <IconButton onClick={() => saveRule(idx)} color="primary">
                                <Save />
                              </IconButton>
                              <IconButton
                                onClick={() => {
                                  setEditingRule(null);
                                  setParamsError(null);
                                }}
                                color="error"
                              >
                                <Cancel />
                              </IconButton>
                            </Stack>
                          </Stack>
                        ) : (
                          <Card variant="outlined" sx={{ p: 1.5 }}>
                            <Stack
                              direction="row"
                              justifyContent="space-between"
                              alignItems="flex-start"
                              spacing={1}
                            >
                              <ListItemText
                                primary={
                                  <Typography variant="subtitle1">
                                    {rule.type}{" "}
                                    <Typography component="span" variant="subtitle2" color="text.secondary">
                                      ({rule.kind})
                                    </Typography>
                                  </Typography>
                                }
                                secondary={rule.description}
                              />
                              <IconButton onClick={() => startEditRule(rule, idx)}>
                                <Edit />
                              </IconButton>
                            </Stack>

                            <Box
                              sx={{
                                mt: 1,
                                p: 1.5,
                                bgcolor: "#f9fafb",
                                border: "1px solid #e5e7eb",
                                borderRadius: 1,
                                overflowX: "auto",
                              }}
                            >
                              <Typography variant="subtitle2" gutterBottom>
                                Params
                              </Typography>
                              <Typography
                                component="pre"
                                sx={{
                                  m: 0,
                                  whiteSpace: "pre-wrap",
                                  wordBreak: "break-word",
                                  fontFamily: "monospace",
                                  fontSize: 13,
                                }}
                              >
                                {JSON.stringify(rule?.params ?? {}, null, 2)}
                              </Typography>
                            </Box>
                          </Card>
                        )}
                      </Box>
                    ))}
                  </List>
                </CardContent>
              </Card>
            ) : (
              <Card variant="outlined" sx={{ p: 3 }}>
                <Typography color="text.secondary">
                  Select a rule set on the left to see details.
                </Typography>
              </Card>
            )}
          </Box>
        </Box>

        <Box mt={2}>
          <Button variant="contained" onClick={fetchRuleSets}>
            Refresh
          </Button>

          <CreateRuleSet
            open={createOpen}
            onClose={() => setCreateOpen(false)}
            existingNames={existingNames}
            onCreated={(newRs) => {
              fetchRuleSets().then(() => setSelectedRuleSet(newRs));
            }}
          />
        </Box>
      </Box>
    </div>
  );
}
