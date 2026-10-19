O1 — Lookup arrays em problem_data (problem.py, load_problem)                                                                                                                                                      
  Pré-computar dois arrays numpy de tamanho n_genes:
  gene_shift_arr[gene_val] = s_idx            
  gene_team_arr[gene_val]  = t_idx        
  Custo zero em runtime. Prerequisito para O2–O5.                                                                                                                                                                    
                                                                                                                                                                                                                     
  ---                                                                                                                                                                                                                
  O2 — _compute_penalties vetorizado (problem.py) — impacto mais alto                                                                                                                                                
  # Antes: loop n_shifts×n_teams, np.sum(schedule == gene_val) por gene                                                                                                                                              
  # Depois:                                                            
  emp_i, day_j = np.where(schedule != GENE_OFF)                                                                                                                                                                      
  genes = schedule[emp_i, day_j]                                                                                                                                                                                     
  coverage = np.bincount(       
      np.ravel_multi_index((day_j, gene_shift_arr[genes], gene_team_arr[genes]),                                                                                                                                     
                           (n_days, n_shifts, n_teams)),                        
      minlength=n_days * n_shifts * n_teams                                                                                                                                                                          
  ).reshape(n_days, n_shifts, n_teams)                                                                                                                                                                               
  min_unmet   = int(np.sum(np.maximum(0, min_demand   - coverage)))
  ideal_unmet = int(np.sum(np.maximum(0, ideal_demand - coverage)))                                                                                                                                                  
  np.bincount é O(n) e muito mais rápido que n_shifts×n_teams somas separadas.                                                                                                                                       
                                          
  ---                                                                                                                                                                                                                
  O3 — _update_coverage vetorizado (ga.py)                                                                                                                                                                           
  # Antes: loop n_genes, np.where por gene    
  # Depois:                                                                                                                                                                                                          
  mask = row_arr != GENE_OFF
  days = np.where(mask)[0]                                                                                                                                                                                           
  if len(days):           
      genes = row_arr[days]                                                                                                                                                                                          
      np.add.at(coverage, (days, gene_shift_arr[genes], gene_team_arr[genes]), 1)
                                                                                 
  ---                                                                                                                                                                                                                
  O4 — _coverage_contribution vetorizado (ga.py)
  # Antes: loop n_genes, np.where + slicing por gene                                                                                                                                                                 
  # Depois:                                         
  days = np.where(row_arr != GENE_OFF)[0]                                                                                                                                                                            
  if not len(days):                       
      return 0                                                                                                                                                                                                       
  genes = row_arr[days]                                                                                                                                                                                              
  s_arr, t_arr = gene_shift_arr[genes], gene_team_arr[genes]
  cov = coverage[days, s_arr, t_arr]                                                                                                                                                                                 
  mn  = min_demand[days, s_arr, t_arr]        
  id_ = ideal_demand[days, s_arr, t_arr]  
  return int(np.sum(np.maximum(0, mn - cov)) * 100 +
             np.sum(np.maximum(0, id_ - np.maximum(cov, mn))))                                                                                                                                                       
   
  ---                                                                                                                                                                                                                
  O5 — Máscara de mutação vetorizada (ga.py, mut_demand_guided)
  # Antes: if random.random() >= indpb: continue  → 69M chamadas Python                                                                                                                                              
  # Depois: gerar máscara toda de uma vez                                                                                                                                                                            
  mut_mask = (np.random.random((n_emp, n_days)) < indpb) & ~vac_mask
  positions = np.argwhere(mut_mask)  # só iterar onde há mutação                                                                                                                                                     
                                          
  ---                                                                                                                                                                                                                
  O6 — Coverage inicial em mut_demand_guided vetorizado (ga.py)                                                                                                                                                      
  # Antes: loop n_genes, np.sum(schedule == gene_val, axis=0)                                                                                                                                                        
  # Depois: mesmo padrão do O2 com np.bincount                                                                                                                                                                       
                                              
  ---                                                       