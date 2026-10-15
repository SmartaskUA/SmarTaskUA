import React from "react";

// Template names have no spaces, so give the browser a line-break opportunity after each
// underscore; that keeps parts like "Case1" or "192" whole instead of cutting them mid-word.
const BreakableName = ({ name }) =>
  String(name ?? "")
    .split("_")
    .map((part, index, parts) => (index < parts.length - 1 ? `${part}_` : part))
    .map((part, index) => (
      <React.Fragment key={index}>
        {index > 0 && <wbr />}
        {part}
      </React.Fragment>
    ));

export default BreakableName;
