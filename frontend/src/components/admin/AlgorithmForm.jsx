import React, { useState } from "react";

const AlgorithmForm = () => {
  const [color, setColor] = useState("#d8b3ff");

  return (
    <div className="algorithm-form-container">
      <div className="color-preview">
        <div className="color-box" style={{ backgroundColor: color }}></div>
        <span className="color-label">Selected Color</span>
      </div>

      <div className="form-section">
        <h3>Informations</h3>
        
        <label className="form-label">
          Name:
          <input className="form-input" type="text" />
        </label>
        
        <label className="form-label">
          Description:
          <input className="form-input" type="text" />
        </label>

        <label className="form-label">
          Color:
          <input 
            className="color-input" 
            type="color" 
            value={color} 
            onChange={(e) => setColor(e.target.value)} 
          />
        </label>

        <label className="form-label">
          Logo:
          <input className="file-input" type="file" />
        </label>
        
        <div className="button-group">
          <button className="form-button">Import</button>
          <button className="form-button">Remove</button>
        </div>
      </div>

      <div className="action-buttons">
        <button className="action-button">Add</button>
        <button className="action-button cancel-button">Cancel</button>
      </div>
    </div>
  );
};

export default AlgorithmForm;
