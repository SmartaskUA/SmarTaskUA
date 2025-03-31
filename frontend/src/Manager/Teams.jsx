import React, { useEffect, useState } from "react";
import Sidebar_Manager from "../components/Sidebar_Manager"; 
import BaseUrl from "../components/BaseUrl";

const Teams = () => {
  const [teams, setTeams] = useState([]);

  useEffect(() => {

    // usar axios e melhor o frontend/
    const fetchTeams = async () => {
      try {
        const response = await fetch('http://localhost:8081/api/v1/teams/', {
          method: 'GET',
          headers: {
            'Accept': '*/*',
          },
        });
        
        const data = await response.json();
        setTeams(data);
      } catch (error) {
        console.error('Error fetching teams:', error);
      }
    };

    fetchTeams();
  }, []);

  return (
    <div className="admin-container">
      <Sidebar_Manager />  
      <div className="main-content">
        <h2 className="heading">Teams</h2>
        <div className="teams-list">
          {teams.length > 0 ? (
            teams.map((team) => (
              <div key={team.id} className="team-item">
                <div className="team-card">
                  <h3 className="team-name">{team.name}</h3>
                  <p className="team-employees">
                    {team.employees.length} {team.employees.length === 1 ? 'Employee' : 'Employees'}
                  </p>
                </div>
              </div>
            ))
          ) : (
            <p className="loading-message">Loading teams...</p>
          )}
        </div>
      </div> 
    </div>
  );
};

export default Teams;
