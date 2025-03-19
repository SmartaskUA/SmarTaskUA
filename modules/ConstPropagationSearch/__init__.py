from GenerateVariables_based_csv import ScheduleVariables

# Define the CSV path (adjust if needed)
CSV_PATH = "ex1.csv"

# Initialize and execute variable generation
def main():
    print("📌 Initializing SmarTask Scheduling System...\n")

    # 🔹 Generate variables for scheduling
    print("🔍 Generating scheduling variables...")
    generator = ScheduleVariables(CSV_PATH)
    variables = generator.get_variables()

    # 🔹 Print the generated variables (optional)
    print("✅ Variables successfully generated:")
    print(variables)

    # 🔹 Future calls (when modules are implemented)
    # from constraint_solver import ConstraintSolver
    # from schedule_optimizer import ScheduleOptimizer
    # solver = ConstraintSolver(variables)
    # optimized_schedule = solver.solve()
    # optimizer = ScheduleOptimizer(optimized_schedule)
    # final_schedule = optimizer.optimize()

    print("\n🚀 SmarTask execution complete!")

# Execute when running as a script
if __name__ == "__main__":
    main()
