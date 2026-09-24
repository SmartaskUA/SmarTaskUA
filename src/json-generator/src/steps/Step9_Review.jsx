import React, { useState } from 'react';
import { Alert } from '@mui/material';
import JSZip from 'jszip';
import { saveAs } from 'file-saver';
import StepLayout from '../components/wizard/StepLayout';
import StepCard from '../components/wizard/StepCard';
import SummaryAccordions from '../components/review/SummaryAccordions';
import ValidationPanel from '../components/review/ValidationPanel';
import PreviewTabs from '../components/review/PreviewTabs';
import DownloadPanel from '../components/review/DownloadPanel';
import { useWizard } from '../context/WizardContext';
import { bundleEntries } from '../v4/generate';

/**
 * Step 9: Review — validate the generated bundle and download it. The ZIP is
 * flat, so an unzipped copy validates as a package with `make validate DIR=…`.
 */
const Step9_Review = () => {
  const { state, validation, findings, goToStep } = useWizard();
  const { bundle, report } = validation;
  const [zipping, setZipping] = useState(false);
  const blocked = !bundle || report.errors.length > 0;

  const downloadZip = async () => {
    setZipping(true);
    try {
      const zip = new JSZip();
      for (const [name, text] of bundleEntries(bundle)) zip.file(name, text);
      saveAs(await zip.generateAsync({ type: 'blob' }), `${state.metadata.problemId || 'problem'}_v4.zip`);
    } finally {
      setZipping(false);
    }
    return false;
  };

  return (
    <StepLayout
      title="Review & download"
      subtitle="The files below are what gets downloaded, and what the validator checked."
      showFindings={false}
      onNext={downloadZip}
      nextDisabled={blocked || zipping}
      nextLabel={zipping ? 'Creating ZIP…' : 'Download ZIP'}
    >
      <StepCard>
        <ValidationPanel report={report} onJump={goToStep} />
        {bundle && <PreviewTabs bundle={bundle} />}
        {bundle && <DownloadPanel bundle={bundle} disabled={blocked} />}
        {blocked && bundle && (
          <Alert severity="warning" sx={{ mt: 2 }}>
            Downloads unlock once there are no errors. The previews stay available meanwhile.
          </Alert>
        )}
      </StepCard>
      <SummaryAccordions state={state} findings={findings} onJump={goToStep} />
    </StepLayout>
  );
};

export default Step9_Review;
