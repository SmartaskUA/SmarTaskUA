import React, { useState } from 'react';
import { Tabs, Tab, Card, CardContent } from '@mui/material';
import { Description, TableChart } from '@mui/icons-material';
import JsonPreview from '../preview/JsonPreview';
import CsvPreview from '../preview/CsvPreview';

/** One tab per file in the bundle, problem.json first. */
const PreviewTabs = ({ bundle }) => {
  const [active, setActive] = useState(0);
  const names = [bundle.problemName, ...Object.keys(bundle.files)];
  const current = names[Math.min(active, names.length - 1)];
  return (
    <Card variant="outlined" sx={{ mb: 3 }}>
      <Tabs value={Math.min(active, names.length - 1)} onChange={(_, v) => setActive(v)} variant="scrollable" scrollButtons="auto" sx={{ borderBottom: 1, borderColor: 'divider' }}>
        {names.map((n, i) => (
          <Tab key={n} icon={i === 0 ? <Description /> : <TableChart />} iconPosition="start" label={n} sx={{ textTransform: 'none' }} />
        ))}
      </Tabs>
      <CardContent>
        {current === bundle.problemName
          ? <JsonPreview json={bundle.problem} />
          : <CsvPreview csv={bundle.files[current]} filename={current} />}
      </CardContent>
    </Card>
  );
};

export default PreviewTabs;
