// CreateRuleSet.jsx
import React, { useEffect, useMemo, useState } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Stack,
  Box,
  IconButton,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  Collapse,
  Divider,
  Card,
  CardContent,
  CircularProgress,
  Tooltip,
} from "@mui/material";
import { Add, Delete, Save } from "@mui/icons-material";
import axios from "axios";
import BaseUrl from "../components/BaseUrl";

export default function CreateRuleSet({
  open,
  onClose,
  onCreated,          // (newRuleSet) => void
  existingNames = [], // optional for duplicate-name check
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [rules, setRules] = useState([
    { type: "", kind: "soft", description: "", paramsJson: "{\n}" },
  ]);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [fieldErrors, setFieldErrors] = useState({}); // {name: 'msg', rule_0_params: 'msg', ...}

  // available rules (types) and metadata (description/params) indexed by type
  const [availableRules, setAvailableRules] = useState([]); // string[]
  const [catalogByType, setCatalogByType] = useState({});   // { [type]: { description, params } }
  const [loadingAvail, setLoadingAvail] = useState(false);
  const [availError, setAvailError] = useState(null);

  // Fetch available rules (full objects) when dialog opens
  useEffect(() => {
    if (!open) return;

    const load = async () => {
      setLoadingAvail(true);
      setAvailError(null);
      try {
        // NOW returns full rules: [{ type, kind?, description, params }, ...]
        const res = await axios.get(`${BaseUrl}/rulesets/rules/available`);
        const arr = Array.isArray(res.data) ? res.data : [];

        // Dropdown options:
        const types = arr
          .map((r) => r?.type)
          .filter(Boolean);

        // Auto-fill metadata:
        const map = {};
        arr.forEach((r) => {
          if (!r?.type) return;
          map[r.type] = {
            description: r.description || "",
            params: r.params || {},
          };
        });

        setAvailableRules(types);
        setCatalogByType(map);
      } catch (e) {
        setAvailError("Failed to load available rules.");
        setAvailableRules([]);
        setCatalogByType({});
      } finally {
        setLoadingAvail(false);
      }
    };

    load();
  }, [open]);

  const resetForm = () => {
    setName("");
    setDescription("");
    setRules([{ type: "", kind: "soft", description: "", paramsJson: "{\n}" }]);
    setError(null);
    setFieldErrors({});
  };

  const handleClose = () => {
    if (!submitting) {
      resetForm();
      onClose?.();
    }
  };

  const selectedTypes = useMemo(() => rules.map((r) => r.type).filter(Boolean), [rules]);

  const remainingTypes = useMemo(() => {
    return availableRules.filter((t) => !selectedTypes.includes(t));
  }, [availableRules, selectedTypes]);

  const isEmptyParamsJson = (val) => {
    if (val == null) return true;
    const trimmed = String(val).trim();
    if (trimmed === "" || trimmed === "{}" || trimmed === "{\n}" || trimmed === "{ }") {
      return true;
    }
    try {
      const parsed = JSON.parse(trimmed);
      return parsed && Object.keys(parsed).length === 0;
    } catch {
      return false; // invalid JSON is not "empty"
    }
  };

  const autoFillFromCatalog = (idx, type) => {
    const meta = catalogByType?.[type];
    if (!meta) return;

    setRules((prev) =>
      prev.map((r, i) => {
        if (i !== idx) return r;
        const next = { ...r };

        // Only fill if currently empty to avoid overwriting user input
        if (!next.description?.trim()) {
          next.description = meta.description || "";
        }
        if (isEmptyParamsJson(next.paramsJson)) {
          next.paramsJson = JSON.stringify(meta.params || {}, null, 2);
        }
        return next;
      })
    );
  };

  const addRule = () => {
    // If we have a fixed catalog list, prefill with the first remaining type, else blank
    const nextType = remainingTypes.length > 0 ? remainingTypes[0] : "";
    setRules((prev) => [
      ...prev,
      { type: nextType, kind: "soft", description: "", paramsJson: "{\n}" },
    ]);
    // After adding, if we picked a type, auto-fill from catalog for the last index
    const idx = rules.length; // new index
    if (nextType) {
      setTimeout(() => autoFillFromCatalog(idx, nextType), 0);
    }
  };

  const removeRule = (idx) => {
    setRules((prev) => prev.filter((_, i) => i !== idx));
    setFieldErrors((prev) => {
      const copy = { ...prev };
      Object.keys(copy).forEach((k) => {
        if (k.startsWith(`rule_${idx}_`)) delete copy[k];
      });
      return copy;
    });
  };

  const updateRule = (idx, patch) => {
    setRules((prev) =>
      prev.map((r, i) => (i === idx ? { ...r, ...patch } : r))
    );
  };

  const hasDuplicateTypes = useMemo(() => {
    const seen = new Set();
    for (const t of selectedTypes) {
      if (!t) continue;
      if (seen.has(t)) return true;
      seen.add(t);
    }
    return false;
  }, [selectedTypes]);

  const validate = () => {
    const errs = {};
    if (!name.trim()) errs.name = "Name is required.";
    if (existingNames.includes(name.trim()))
      errs.name = "A ruleset with this name already exists.";

    if (hasDuplicateTypes) {
      errs.rules = "Rule types must be unique.";
    }

    rules.forEach((r, i) => {
      if (!r.type.trim()) errs[`rule_${i}_type`] = "Type is required.";
      if (!r.kind) errs[`rule_${i}_kind`] = "Kind is required.";
      if (!r.description.trim())
        errs[`rule_${i}_description`] = "Description is required.";
      try {
        if (r.paramsJson && r.paramsJson.trim()) JSON.parse(r.paramsJson);
      } catch (e) {
        errs[`rule_${i}_params`] = e?.message || "Invalid JSON in params.";
      }
    });

    setFieldErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const payload = useMemo(() => {
    try {
      const normalizedRules = rules.map((r) => ({
        type: r.type.trim(),
        kind: r.kind,
        description: r.description.trim(),
        params: r.paramsJson && r.paramsJson.trim() ? JSON.parse(r.paramsJson) : {},
      }));
      return {
        name: name.trim(),
        description: description.trim(),
        rules: normalizedRules,
      };
    } catch {
      return null;
    }
  }, [name, description, rules]);

  const handleCreate = async () => {
    setError(null);
    if (!validate()) return;
    if (!payload) {
      setError("Unable to build payload. Check your fields.");
      return;
    }

    // extra guard against duplicates on submit
    const types = payload.rules.map((r) => r.type);
    const unique = new Set(types);
    if (unique.size !== types.length) {
      setError("Rule types must be unique.");
      return;
    }

    try {
      setSubmitting(true);
      const res = await axios.post(`${BaseUrl}/rulesets`, payload);
      const created = res?.data ?? payload;
      onCreated?.(created);
      resetForm();
      onClose?.();
    } catch (e) {
      setError(
        e?.response?.data?.message ||
          e?.message ||
          "Failed to create ruleset."
      );
    } finally {
      setSubmitting(false);
    }
  };

  const usingCatalog = availableRules.length > 0;

  return (
    <Dialog open={open} onClose={handleClose} fullWidth maxWidth="md">
      <DialogTitle>Create New Rule Set</DialogTitle>
      <DialogContent dividers>
        <Collapse in={!!error} unmountOnExit>
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        </Collapse>

        <Stack spacing={2}>
          <TextField
            label="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            error={!!fieldErrors.name}
            helperText={fieldErrors.name}
            autoFocus
          />
          <TextField
            label="Description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            multiline
            minRows={2}
          />

          <Divider />

          <Stack direction="row" alignItems="center" justifyContent="space-between">
            <Typography variant="h6">Rules</Typography>

            <Tooltip
              title={
                usingCatalog
                  ? remainingTypes.length === 0
                    ? "All available rule types are already added."
                    : ""
                  : availError
                  ? "Rule catalog unavailable, using free-text types."
                  : "No catalog returned, using free-text types."
              }
            >
              <span>
                <Button
                  startIcon={<Add />}
                  onClick={addRule}
                  disabled={usingCatalog && remainingTypes.length === 0}
                >
                  Add Rule
                </Button>
              </span>
            </Tooltip>
          </Stack>

          {loadingAvail && (
            <Stack direction="row" alignItems="center" spacing={1}>
              <CircularProgress size={18} />
              <Typography variant="body2">Loading rule options…</Typography>
            </Stack>
          )}

          {!!availError && (
            <Alert severity="warning" sx={{ mb: 1 }}>
              {availError} You can still type rule names manually.
            </Alert>
          )}

          {hasDuplicateTypes && (
            <Alert severity="error">Rule types must be unique.</Alert>
          )}

          {rules.map((rule, idx) => {
            const disableTypeError = !!fieldErrors[`rule_${idx}_type`];
            const disableKindError = !!fieldErrors[`rule_${idx}_kind`];
            const dupThisType =
              rule.type &&
              selectedTypes.filter((t) => t === rule.type).length > 1;

            return (
              <Card key={idx} variant="outlined">
                <CardContent>
                  <Stack spacing={1}>
                    <Stack
                      direction={{ xs: "column", sm: "row" }}
                      spacing={1}
                      alignItems={{ xs: "stretch", sm: "center" }}
                    >
                      {usingCatalog ? (
                        <FormControl
                          size="small"
                          sx={{ minWidth: 220 }}
                          error={disableTypeError || dupThisType}
                        >
                          <InputLabel id={`type-label-${idx}`}>Type</InputLabel>
                          <Select
                            labelId={`type-label-${idx}`}
                            label="Type"
                            value={rule.type}
                            onChange={(e) => {
                              const newType = e.target.value;
                              updateRule(idx, { type: newType });
                              // clear type error on change
                              setFieldErrors((prev) => {
                                const copy = { ...prev };
                                delete copy[`rule_${idx}_type`];
                                return copy;
                              });
                              // auto-fill description/params from catalog we just built
                              autoFillFromCatalog(idx, newType);
                            }}
                          >
                            {availableRules.map((t) => {
                              const isSelectedElsewhere =
                                selectedTypes.includes(t) && t !== rule.type;
                              return (
                                <MenuItem key={t} value={t} disabled={isSelectedElsewhere}>
                                  {t}
                                </MenuItem>
                              );
                            })}
                          </Select>
                          <Collapse in={dupThisType}>
                            <Typography color="error" variant="caption">
                              This type is already selected in another rule.
                            </Typography>
                          </Collapse>
                          {disableTypeError && (
                            <Typography color="error" variant="caption">
                              {fieldErrors[`rule_${idx}_type`]}
                            </Typography>
                          )}
                        </FormControl>
                      ) : (
                        <TextField
                          label="Type"
                          value={rule.type}
                          onChange={(e) => {
                            const newType = e.target.value;
                            updateRule(idx, { type: newType });
                            // if user typed a type that exists in catalog, auto-fill
                            if (catalogByType[newType]) {
                              autoFillFromCatalog(idx, newType);
                            }
                          }}
                          error={disableTypeError || dupThisType}
                          helperText={
                            dupThisType
                              ? "This type is already selected in another rule."
                              : fieldErrors[`rule_${idx}_type`] || ""
                          }
                          size="small"
                          sx={{ minWidth: 220 }}
                        />
                      )}

                      <FormControl
                        size="small"
                        sx={{ minWidth: 140 }}
                        error={disableKindError}
                      >
                        <InputLabel id={`kind-label-${idx}`}>Kind</InputLabel>
                        <Select
                          labelId={`kind-label-${idx}`}
                          label="Kind"
                          value={rule.kind}
                          onChange={(e) => {
                            updateRule(idx, { kind: e.target.value });
                            setFieldErrors((prev) => {
                              const copy = { ...prev };
                              delete copy[`rule_${idx}_kind`];
                              return copy;
                            });
                          }}
                        >
                          <MenuItem value="soft">Soft</MenuItem>
                          <MenuItem value="hard">Hard</MenuItem>
                        </Select>
                      </FormControl>

                      <Box flex={1} />
                      <IconButton
                        color="error"
                        onClick={() => removeRule(idx)}
                        disabled={rules.length === 1}
                        title="Remove rule"
                        size="small"
                      >
                        <Delete />
                      </IconButton>
                    </Stack>

                    <TextField
                      label="Rule Description"
                      value={rule.description}
                      onChange={(e) => {
                        updateRule(idx, { description: e.target.value });
                        setFieldErrors((prev) => {
                          const copy = { ...prev };
                          delete copy[`rule_${idx}_description`];
                          return copy;
                        });
                      }}
                      error={!!fieldErrors[`rule_${idx}_description`]}
                      helperText={fieldErrors[`rule_${idx}_description`] || ""}
                      fullWidth
                      size="small"
                    />

                    <TextField
                      label="Params (JSON)"
                      value={rule.paramsJson}
                      onChange={(e) => {
                        const val = e.target.value;
                        updateRule(idx, { paramsJson: val });
                        // live-validate for quick feedback
                        try {
                          JSON.parse(val || "{}");
                          setFieldErrors((prev) => {
                            const { [`rule_${idx}_params`]: _, ...rest } = prev;
                            return rest;
                          });
                        } catch (err) {
                          setFieldErrors((prev) => ({
                            ...prev,
                            [`rule_${idx}_params`]:
                              err?.message || "Invalid JSON",
                          }));
                        }
                      }}
                      multiline
                      minRows={5}
                      placeholder={`e.g. {\n  "threshold": 0.8,\n  "enabled": true\n}`}
                      sx={{ fontFamily: "monospace" }}
                      error={!!fieldErrors[`rule_${idx}_params`]}
                      helperText={fieldErrors[`rule_${idx}_params`] || ""}
                    />
                  </Stack>
                </CardContent>
              </Card>
            );
          })}
        </Stack>
      </DialogContent>

      <DialogActions>
        <Button onClick={handleClose} disabled={submitting}>Cancel</Button>
        <Button
          startIcon={<Save />}
          variant="contained"
          onClick={handleCreate}
          disabled={submitting || (usingCatalog && hasDuplicateTypes)}
        >
          Create
        </Button>
      </DialogActions>
    </Dialog>
  );
}
