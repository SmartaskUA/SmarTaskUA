import React, { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Collapse,
  Divider,
  InputAdornment,
  List,
  ListItemButton,
  ListItemText,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import baseurl from "../components/BaseUrl";
import Sidebar_Manager from "../components/Sidebar_Manager";
import "./Problems.css";

const Problems = () => {
  const [problems, setProblems] = useState([]);
  const [selectedProblemId, setSelectedProblemId] = useState("");
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [problemJson, setProblemJson] = useState(null);
  const [jsonError, setJsonError] = useState("");
  const [jsonLoading, setJsonLoading] = useState(false);
  const [showJson, setShowJson] = useState(false);
  const navigate = useNavigate();

  const fetchProblems = async () => {
    try {
      setLoading(true);
      const res = await axios.get(`${baseurl}/problems`);
      const list = Array.isArray(res.data) ? res.data : [];
      setProblems(list);
      if (!selectedProblemId && list.length) {
        setSelectedProblemId(list[0].problemId);
      }
      setError("");
    } catch (err) {
      console.error("Failed to fetch problems:", err);
      setError("Failed to load problems.");
    } finally {
      setLoading(false);
    }
  };

  const fetchProblemJson = async (problemId) => {
    if (!problemId) return;
    try {
      setJsonLoading(true);
      const res = await axios.get(`${baseurl}/problems/${encodeURIComponent(problemId)}/json`);
      setProblemJson(res.data);
      setJsonError("");
    } catch (err) {
      console.error("Failed to fetch problem JSON:", err);
      setProblemJson(null);
      setJsonError("Failed to load problem.json.");
    } finally {
      setJsonLoading(false);
    }
  };

  useEffect(() => {
    fetchProblems();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    setProblemJson(null);
    setJsonError("");
    setShowJson(false);
    if (selectedProblemId) {
      fetchProblemJson(selectedProblemId);
    }
  }, [selectedProblemId]);

  const filteredProblems = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return problems;
    return problems.filter((p) => {
      const id = String(p.problemId || "").toLowerCase();
      const name = String(p.name || "").toLowerCase();
      const desc = String(p.description || "").toLowerCase();
      return id.includes(term) || name.includes(term) || desc.includes(term);
    });
  }, [problems, search]);

  const selectedProblem = useMemo(
    () => problems.find((p) => p.problemId === selectedProblemId),
    [problems, selectedProblemId]
  );
  const bundleFolder = useMemo(() => {
    if (!selectedProblem?.problemPath) return "";
    const parts = selectedProblem.problemPath.split(/[/\\\\]/);
    parts.pop();
    return parts.join("/");
  }, [selectedProblem]);

  const problemMeta = useMemo(() => {
    if (!problemJson || typeof problemJson !== "object") return null;
    const metadata =
      problemJson.metadata && typeof problemJson.metadata === "object" ? problemJson.metadata : {};
    const temporal =
      problemJson.temporalScope && typeof problemJson.temporalScope === "object"
        ? problemJson.temporalScope
        : {};
    const demand =
      problemJson.demand && typeof problemJson.demand === "object" ? problemJson.demand : {};
    const constraints =
      problemJson.constraints && typeof problemJson.constraints === "object"
        ? problemJson.constraints
        : {};
    const shifts = Array.isArray(demand.shifts) ? demand.shifts.length : null;
    const hardCount = Array.isArray(constraints.hard) ? constraints.hard.length : 0;
    const softCount = Array.isArray(constraints.soft) ? constraints.soft.length : 0;
    const dataFiles = new Set();
    const collectFiles = (node) => {
      if (Array.isArray(node)) {
        node.forEach(collectFiles);
        return;
      }
      if (node && typeof node === "object") {
        Object.entries(node).forEach(([key, value]) => {
          if (key === "dataFile" && typeof value === "string" && value.trim()) {
            dataFiles.add(value);
          } else {
            collectFiles(value);
          }
        });
      }
    };
    collectFiles(problemJson);
    return {
      name: typeof metadata.name === "string" ? metadata.name : "",
      description: typeof metadata.description === "string" ? metadata.description : "",
      source: typeof metadata.source === "string" ? metadata.source : "",
      year: temporal.year != null ? String(temporal.year) : "",
      shifts,
      hardCount,
      softCount,
      dataFiles: Array.from(dataFiles),
    };
  }, [problemJson]);

  const hardCount = problemMeta?.hardCount || 0;
  const softCount = problemMeta?.softCount || 0;

  const handleUseProblem = () => {
    if (!selectedProblem?.problemId) return;
    navigate(`/manager/createCalendar?problemId=${encodeURIComponent(selectedProblem.problemId)}`);
  };

  const handleToggleJson = () => {
    if (!selectedProblem?.problemId) return;
    const next = !showJson;
    setShowJson(next);
    if (next && !problemJson && !jsonLoading) {
      fetchProblemJson(selectedProblem.problemId);
    }
  };

  return (
    <div className="admin-container problems-page">
      <Sidebar_Manager />
      <Box className="main-content problems-main" sx={{ marginRight: 3 }}>
        <Stack
          direction={{ xs: "column", sm: "row" }}
          alignItems={{ xs: "flex-start", sm: "center" }}
          justifyContent="space-between"
          gap={2}
          mb={2}
        >
          <Box>
            <Typography variant="h4" className="problems-title">
              Problems
            </Typography>
            <Typography variant="body2" className="problems-subtitle">
              Browse the problem library and launch a schedule in one click.
            </Typography>
          </Box>
          <Button
            variant="outlined"
            onClick={fetchProblems}
            disabled={loading}
            className="problems-action ghost"
          >
            Refresh
          </Button>
        </Stack>

        <Collapse in={!!error}>
          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
        </Collapse>

        <Box
          display="flex"
          flexDirection={{ xs: "column", md: "row" }}
          gap={4}
          alignItems="stretch"
        >
          <Card
            className="problems-card slim problems-panel"
            elevation={0}
            sx={{ width: { xs: "100%", md: 420 }, maxHeight: { xs: "none", md: "80vh" }, display: "flex", flexDirection: "column" }}
          >
            <CardContent sx={{ pb: 1 }}>
              <Stack spacing={1.5}>
                <TextField
                  size="small"
                  placeholder="Search problems..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <SearchIcon fontSize="small" />
                      </InputAdornment>
                    ),
                  }}
                  sx={{
                    "& .MuiOutlinedInput-root": {
                      borderRadius: "999px",
                      backgroundColor: "rgba(255,255,255,0.9)",
                    },
                    "& .MuiInputAdornment-root": {
                      color: "rgba(15, 118, 110, 0.7)",
                    },
                  }}
                />
                <Divider />
                <List dense className="problems-list" sx={{ maxHeight: { xs: "none", md: "60vh" }, overflowY: "auto" }}>
                  {filteredProblems.map((problem, index) => (
                    <ListItemButton
                      key={problem.problemId}
                      selected={problem.problemId === selectedProblemId}
                      onClick={() => setSelectedProblemId(problem.problemId)}
                      className="problems-stagger"
                      style={{ animationDelay: `${index * 0.03}s` }}
                    >
                      <ListItemText
                        primary={problem.name || problem.problemId}
                        secondary={problem.description || (problem.name ? problem.problemId : "")}
                        primaryTypographyProps={{ fontWeight: 600 }}
                      />
                    </ListItemButton>
                  ))}
                  {!filteredProblems.length && (
                    <Typography variant="body2" color="text.secondary">
                      No problems found.
                    </Typography>
                  )}
                </List>
              </Stack>
            </CardContent>
          </Card>

          <Card className="problems-card problems-panel" elevation={0} sx={{ flex: 1, minHeight: 300 }}>
            <CardContent>
              {selectedProblem ? (
                <Stack spacing={2}>
                  <Stack direction="row" alignItems="center" justifyContent="space-between" gap={2}>
                    <Typography variant="h5" className="problems-title">
                      {problemMeta?.name || selectedProblem.problemId}
                    </Typography>
                    <Button
                      variant="contained"
                      onClick={handleUseProblem}
                      className="problems-action primary"
                    >
                      Use In Schedule
                    </Button>
                  </Stack>
                  {(problemMeta?.description || selectedProblem.description) && (
                    <Typography variant="body2" color="text.secondary">
                      {problemMeta?.description || selectedProblem.description}
                    </Typography>
                  )}
                  <Divider />
                  <Stack direction="row" flexWrap="wrap" gap={1}>
                    {problemMeta?.shifts != null && (
                      <Chip label={`Shifts: ${problemMeta.shifts}`} className="problems-chip" />
                    )}
                    {problemMeta?.year && (
                      <Chip label={`Year: ${problemMeta.year}`} className="problems-chip" />
                    )}
                    {(hardCount || softCount) && (
                      <Chip
                        label={`Constraints: ${hardCount} hard, ${softCount} soft`}
                        className="problems-chip"
                      />
                    )}
                  </Stack>
                  <Divider />
                  <Stack spacing={1}>
                    <Typography variant="subtitle2">Files</Typography>
                    <Stack spacing={0.5}>
                      <Typography variant="body2">
                        <strong>Bundle Folder:</strong> {bundleFolder || "N/A"}
                      </Typography>
                      <Typography variant="body2">
                        <strong>Problem File:</strong> {selectedProblem.problemPath || "N/A"}
                      </Typography>
                    </Stack>
                    <Divider />
                    <Typography variant="subtitle2">Data Files</Typography>
                    {problemMeta?.dataFiles?.length ? (
                      <Box display="flex" flexWrap="wrap" gap={1}>
                        {problemMeta.dataFiles.map((file) => (
                          <Chip
                            key={file}
                            label={file}
                            size="small"
                            variant="outlined"
                            className="problems-chip"
                          />
                        ))}
                      </Box>
                    ) : (
                      <Typography variant="body2" color="text.secondary">
                        {jsonLoading ? "Loading data files..." : "No data files referenced in problem.json."}
                      </Typography>
                    )}
                    <Divider />
                    <Typography variant="body2">
                      <strong>Source:</strong> {problemMeta?.source || "N/A"}
                    </Typography>
                    <Divider />
                    <Stack spacing={1}>
                      <Stack direction="row" alignItems="center" justifyContent="space-between">
                        <Typography variant="subtitle2">Problem JSON</Typography>
                        <Stack direction="row" spacing={1}>
                          <Button
                            size="small"
                            variant="outlined"
                            onClick={handleToggleJson}
                            className="problems-action ghost"
                          >
                            {showJson ? "Hide" : "Show"}
                          </Button>
                          <Button
                            size="small"
                            variant="text"
                            onClick={() => fetchProblemJson(selectedProblem.problemId)}
                            disabled={!showJson || jsonLoading}
                            className="problems-action"
                          >
                            Refresh
                          </Button>
                        </Stack>
                      </Stack>
                      <Collapse in={showJson}>
                        {jsonError && (
                          <Typography variant="body2" color="error">
                            {jsonError}
                          </Typography>
                        )}
                        {jsonLoading && (
                          <Typography variant="body2" color="text.secondary">
                            Loading problem.json...
                          </Typography>
                        )}
                        {!jsonLoading && !jsonError && problemJson && (
                          <Box
                            component="pre"
                            className="problems-json"
                            sx={{
                              fontFamily:
                                "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, Courier New, monospace",
                              fontSize: 12,
                              lineHeight: 1.4,
                              maxHeight: 360,
                              overflow: "auto",
                              p: 2,
                              whiteSpace: "pre-wrap",
                            }}
                          >
                            {JSON.stringify(problemJson, null, 2)}
                          </Box>
                        )}
                        {!jsonLoading && !jsonError && !problemJson && (
                          <Typography variant="body2" color="text.secondary">
                            No problem.json loaded.
                          </Typography>
                        )}
                      </Collapse>
                    </Stack>
                  </Stack>
                </Stack>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  Select a problem to see details.
                </Typography>
              )}
            </CardContent>
          </Card>
        </Box>
      </Box>
    </div>
  );
};

export default Problems;
