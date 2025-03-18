import React, { useState } from "react";

const AlgorithmForm = () => {
  const [color, setColor] = useState("#d8b3ff");
  

  return (
    <div>
      <div>
        <div  style={{ backgroundColor: color }}>
          N
        </div>
        <span >Name</span>
      </div>
      <div> 
        <h3>Informations</h3>
        <label>Name:
          <input type="text" />
        </label>
        <label>Description:
          <input type="text" />
        </label>
        <label>Color:
          <input type="color"/>
        </label>
        <label>Logo:
          <input type="file" />
        </label>
        <button >Import</button>
        <button>Remove</button>
      </div>
      <div >
        <button >Add</button>
        <button>Cancel</button>
      </div>
    </div>
  );
};

export default AlgorithmForm;
