import React, { useState } from 'react';
import { Tabs, Tab, Card, CardContent } from '@mui/material';
import { Description, TableChart } from '@mui/icons-material';
import JsonPreview from '../preview/JsonPreview';
import CsvPreview from '../preview/CsvPreview';

/** One tab per file in the bundle: problem.json, result.json when days are fixed, then the CSVs. */
const PreviewTabs = ({ bundle }) => {
  const [active, setActive] = useState(0);
  const docs = { [bundle.problemName]: bundle.problem, ...(bundle.result ? { [bundle.resultName]: bundle.result } : {}) };
  const names = [...Object.keys(docs), ...Object.keys(bundle.files)];
  const current = names[Math.min(active, names.length - 1)];
  return (
    <Card variant="outlined" sx={{ mb: 3 }}>
      <Tabs value={Math.min(active, names.length - 1)} onChange={(_, v) => setActive(v)} variant="scrollable" scrollButtons="auto" sx={{ borderBottom: 1, borderColor: 'divider' }}>
        {names.map((n) => (
          <Tab key={n} icon={n in docs ? <Description /> : <TableChart />} iconPosition="start" label={n} sx={{ textTransform: 'none' }} />
        ))}
      </Tabs>
      <CardContent>
        {current in docs
          ? <JsonPreview json={docs[current]} />
          : <CsvPreview csv={bundle.files[current]} filename={current} />}
      </CardContent>
    </Card>
  );
};

export default PreviewTabs;
