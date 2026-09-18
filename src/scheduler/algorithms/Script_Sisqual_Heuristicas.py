from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = BASE_DIR / "data" / "problems" / "SISQUAL_OCTOBER_2025"


def print_summary(file_path: Path, title: str) -> None:
	df = pd.read_csv(file_path)

	avg_shortage = df.groupby("day_order_mode")["kpi_shortage"].mean()
	idx_min = df.groupby("day_order_mode")["kpi_shortage"].idxmin()
	best_solutions = df.loc[idx_min]

	print(title)
	print(avg_shortage)
	print(best_solutions)

	run_columns = [column for column in df.columns if column != "restart_num"]
	ordered_df = df.sort_values(["restart_num", *run_columns])
	run_signatures = ordered_df.groupby("restart_num", sort=False)[run_columns].apply(
		lambda group: tuple(map(tuple, group.to_numpy()))
	)
	repeated_signatures = run_signatures.value_counts()
	repeated_signatures = repeated_signatures[repeated_signatures > 1]

	print("Repeated runs:")
	if repeated_signatures.empty:
		print("None")
	else:
		for signature, occurrences in repeated_signatures.items():
			restart_nums = run_signatures[run_signatures == signature].index.tolist()
			repeated_times = occurrences - 1
			print(f"- {signature}")
			print(f"  restart_num: {restart_nums}")
			print(f"  occurrences: {occurrences}")
			print(f"  repeated_times: {repeated_times}")

	print()


print_summary(
	DATA_DIR / "heuristic_results_levels.csv",
	"Results for Heuristic with Levels Included:",
)

print_summary(
	DATA_DIR / "heuristic_results_no_levels.csv",
	"Results for Heuristic with No Levels Included:",
)