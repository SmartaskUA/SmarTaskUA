import React, { useState } from 'react';
import { Box, Tabs, Tab, Card, CardContent } from '@mui/material';
import { Description, TableChart } from '@mui/icons-material';
import JsonPreview from '../preview/JsonPreview';
import CsvPreview from '../preview/CsvPreview';

/**
 * Preview Tabs Component
 *
 * Displays tabbed preview of generated files:
 * - Tab 1: problem.json (syntax-highlighted JSON)
 * - Tab 2: demand.csv (table view)
 * - Tab 3: schedule_input.csv (table view)
 */
const PreviewTabs = ({ files }) => {
  const [activeTab, setActiveTab] = useState(0);

  if (!files) {
    return null;
  }

  const { problemJson, demandCsv, scheduleInputCsv } = files;

  return (
    <Card sx={{ mb: 3 }}>
      <Tabs
        value={activeTab}
        onChange={(e, v) => setActiveTab(v)}
        variant="fullWidth"
        sx={{ borderBottom: 1, borderColor: 'divider' }}
      >
        <Tab
          icon={<Description />}
          label="problem.json"
          iconPosition="start"
        />
        <Tab
          icon={<TableChart />}
          label="demand.csv"
          iconPosition="start"
        />
        <Tab
          icon={<TableChart />}
          label="schedule_input.csv"
          iconPosition="start"
        />
      </Tabs>

      <CardContent sx={{ p: 2 }}>
        {activeTab === 0 && problemJson && (
          <JsonPreview json={problemJson} />
        )}

        {activeTab === 1 && demandCsv && (
          <CsvPreview csv={demandCsv} filename="demand.csv" />
        )}

        {activeTab === 2 && scheduleInputCsv && (
          <CsvPreview csv={scheduleInputCsv} filename="schedule_input.csv" />
        )}
      </CardContent>
    </Card>
  );
};

export default PreviewTabs;
