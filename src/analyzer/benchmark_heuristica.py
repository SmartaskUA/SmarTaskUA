"""
Benchmark script for Heuristica algorithm.
Runs the algorithm N times and calculates:
- Average wall time
- Average CPU time
- Average number of minimum requirements failures
"""

import sys
import os
import csv
from statistics import mean, stdev

# Add parent directory to path to import scheduler modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'scheduler'))

from algorithms.Heuristica import Heuristica
from algorithms.ILP_2 import HourlyILPScheduler
from algorithms.utils import rows_to_req_dicts, TEAM_ID_TO_CODE


def load_vacations(filepath):
    """Load vacation data from CSV as list of lists (not dicts)."""
    vacations = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=',')  # Changed from ';' to ','
        next(reader)  # Skip header row
        for row in reader:
            vacations.append(row)
    return vacations


def load_minimums(filepath):
    """Load minimum requirements from CSV as list of lists (not dicts)."""
    minimums = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=',')  # Changed from ';' to ','
        for row in reader:
            minimums.append(row)
    return minimums


def create_employees(num_employees, team_distribution):
    """
    Create employee list with team assignments.
    
    Args:
        num_employees: Total number of employees (e.g., 21)
        team_distribution: Dict with team assignments
            Example: {'A_only': 7, 'B_only': 7, 'both': 7}
    """
    employees = []
    emp_idx = 0
    
    # Team A only
    for _ in range(team_distribution.get('A_only', 0)):
        employees.append({
            'id': emp_idx + 1,
            'teams': ['Team A']  # Pass team names as strings
        })
        emp_idx += 1
    
    # Team B only
    for _ in range(team_distribution.get('B_only', 0)):
        employees.append({
            'id': emp_idx + 1,
            'teams': ['Team B']  # Pass team names as strings
        })
        emp_idx += 1
    
    # Both teams
    for _ in range(team_distribution.get('both', 0)):
        employees.append({
            'id': emp_idx + 1,
            'teams': ['Team A', 'Team B']  # Pass team names as strings
        })
        emp_idx += 1
    
    return employees


def count_minimum_failures(scheduler):
    """
    Count how many times minimum requirements were not met.
    
    Returns:
        int: Total number of hour-team combinations where minimum was not met
    """
    failures = 0
    
    # Build coverage map from assignments
    coverage = {}  # {(date, hour, team_code): count}
    
    for emp_id, assignments in scheduler.assignment.items():
        for (day_1based, block_idx, team_id) in assignments:
            date = scheduler.dates[day_1based - 1]
            block = scheduler.work_blocks[block_idx]
            team_code = TEAM_ID_TO_CODE.get(team_id, 'A')
            
            # Get working hours (excluding break)
            working_hours = scheduler._get_working_hours(block)
            
            for hour in working_hours:
                key = (date, hour, team_code)
                coverage[key] = coverage.get(key, 0) + 1
    
    # Check all minimum requirements
    for (date, hour_str, team_code), minimum in scheduler.minimos.items():
        if minimum <= 0:
            continue  # Skip closed hours
        
        # Extract hour from hour_str (e.g., "09-10" -> 9)
        hour = int(hour_str.split('-')[0])
        
        key = (date, hour, team_code)
        actual = coverage.get(key, 0)
        
        if actual < minimum:
            failures += 1
    
    return failures


def run_benchmark(vacations_file, minimums_file, num_runs=100, 
                  num_employees=21, team_distribution=None, max_time=120):
    """
    Run benchmark N times and calculate statistics.
    
    Args:
        vacations_file: Path to vacations CSV
        minimums_file: Path to minimums CSV
        num_runs: Number of times to run the algorithm
        num_employees: Total number of employees
        team_distribution: Dict with team assignments
        max_time: Maximum time in minutes for each run
    
    Returns:
        dict: Statistics (mean, stdev for times and failures)
    """
    if team_distribution is None:
        team_distribution = {'A_only': 7, 'B_only': 7, 'both': 7}
    
    print(f"\n{'='*80}")
    print(f"HEURISTICA BENCHMARK")
    print(f"{'='*80}")
    print(f"Number of runs: {num_runs}")
    print(f"Employees: {num_employees} ({team_distribution})")
    print(f"Vacations: {vacations_file}")
    print(f"Minimums: {minimums_file}")
    print(f"{'='*80}\n")
    
    # Load data once
    vacations = load_vacations(vacations_file)
    minimums = load_minimums(minimums_file)
    employees = create_employees(num_employees, team_distribution)
    
    wall_times = []
    cpu_times = []
    failures_list = []
    
    for run_idx in range(1, num_runs + 1):
        print(f"[Benchmark] Run {run_idx}/{num_runs}...", end=' ')
        
        # Suppress output
        import io
        import contextlib
        import time
        
        # Measure timing
        start_wall = time.time()
        start_cpu = time.process_time()
        
        with contextlib.redirect_stdout(io.StringIO()):
            # Create and solve HourlyILPScheduler
            scheduler = HourlyILPScheduler(
                vacations_rows=vacations,
                minimums_rows=minimums,
                employees=employees,
                maxTime=max_time,
                year=2025,
                store_hours=13
            )
            scheduler.build_model()
            scheduler.solve()
        
        wall_time = time.time() - start_wall
        cpu_time = time.process_time() - start_cpu
        
        # Count failures
        failures = count_minimum_failures(scheduler)
        
        wall_times.append(wall_time)
        cpu_times.append(cpu_time)
        failures_list.append(failures)
        
        print(f"Wall: {wall_time:.2f}s, CPU: {cpu_time:.2f}s, Failures: {failures}")
    
    # Calculate statistics
    results = {
        'num_runs': num_runs,
        'wall_time_mean': mean(wall_times),
        'wall_time_stdev': stdev(wall_times) if len(wall_times) > 1 else 0,
        'cpu_time_mean': mean(cpu_times),
        'cpu_time_stdev': stdev(cpu_times) if len(cpu_times) > 1 else 0,
        'failures_mean': mean(failures_list),
        'failures_stdev': stdev(failures_list) if len(failures_list) > 1 else 0,
        'wall_times': wall_times,
        'cpu_times': cpu_times,
        'failures': failures_list
    }
    
    return results


def print_results(results):
    """Print benchmark results in a formatted table."""
    print(f"\n{'='*80}")
    print(f"BENCHMARK RESULTS ({results['num_runs']} runs)")
    print(f"{'='*80}")
    print(f"{'Metric':<30} {'Mean':<15} {'Std Dev':<15}")
    print(f"{'-'*80}")
    print(f"{'Wall Time (seconds)':<30} {results['wall_time_mean']:<15.2f} {results['wall_time_stdev']:<15.2f}")
    print(f"{'Wall Time (minutes)':<30} {results['wall_time_mean']/60:<15.2f} {results['wall_time_stdev']/60:<15.2f}")
    print(f"{'CPU Time (seconds)':<30} {results['cpu_time_mean']:<15.2f} {results['cpu_time_stdev']:<15.2f}")
    print(f"{'CPU Time (minutes)':<30} {results['cpu_time_mean']/60:<15.2f} {results['cpu_time_stdev']/60:<15.2f}")
    print(f"{'Minimum Failures':<30} {results['failures_mean']:<15.1f} {results['failures_stdev']:<15.1f}")
    print(f"{'='*80}\n")


def export_results_csv(results, filename="benchmark_results.csv"):
    """Export detailed results to CSV."""
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Run', 'Wall_Time_s', 'CPU_Time_s', 'Failures'])
        
        for i in range(results['num_runs']):
            writer.writerow([
                i + 1,
                f"{results['wall_times'][i]:.2f}",
                f"{results['cpu_times'][i]:.2f}",
                results['failures'][i]
            ])
        
        # Summary row
        writer.writerow([])
        writer.writerow(['SUMMARY', 'Mean', 'Std Dev', ''])
        writer.writerow([
            'Wall Time (s)',
            f"{results['wall_time_mean']:.2f}",
            f"{results['wall_time_stdev']:.2f}",
            ''
        ])
        writer.writerow([
            'CPU Time (s)',
            f"{results['cpu_time_mean']:.2f}",
            f"{results['cpu_time_stdev']:.2f}",
            ''
        ])
        writer.writerow([
            'Failures',
            f"{results['failures_mean']:.1f}",
            f"{results['failures_stdev']:.1f}",
            ''
        ])
    
    print(f"[Benchmark] Results exported to {filename}")


if __name__ == "__main__":
    # Configuration
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    # Paths to data files (adjust as needed)
    VACATIONS_FILE = os.path.join(BASE_DIR, "VacationTemplate_Case1_21.csv")
    MINIMUMS_FILE = os.path.join(BASE_DIR, "Mins_R10-R62.csv")
    
    # Check if files exist, otherwise use alternative paths
    if not os.path.exists(VACATIONS_FILE):
        VACATIONS_FILE = "/home/hugo/Desktop/SmarTaskUA/src/analyzer/VacationTemplate_Case1_21.csv"
    
    if not os.path.exists(MINIMUMS_FILE):
        MINIMUMS_FILE = "/home/hugo/Desktop/SmarTaskUA/src/analyzer/Mins_R10-R62.csv"
    
    # Run benchmark
    NUM_RUNS = 1
    TEAM_DIST = {'A_only': 0, 'B_only': 0, 'both': 21}
    
    results = run_benchmark(
        vacations_file=VACATIONS_FILE,
        minimums_file=MINIMUMS_FILE,
        num_runs=NUM_RUNS,
        num_employees=21,
        team_distribution=TEAM_DIST,
        max_time=120
    )
    
    # Print and export results
    print_results(results)
    export_results_csv(results, os.path.join(BASE_DIR, "benchmark_results.csv"))
