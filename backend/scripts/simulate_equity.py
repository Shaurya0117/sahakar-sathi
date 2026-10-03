import random
import numpy as np
import matplotlib.pyplot as plt

def calculate_gini(incomes):
    """Calculate the Gini coefficient of a numpy array."""
    incomes = np.sort(incomes)
    n = len(incomes)
    index = np.arange(1, n + 1)
    return ((np.sum((2 * index - n  - 1) * incomes)) / (n * np.sum(incomes)))

def run_simulation(strategy="equity", num_jobs=200, num_workers=7):
    # Workers represented by their total earnings
    worker_earnings = np.zeros(num_workers)
    
    # Simple simulation loop
    for job_id in range(num_jobs):
        job_value = random.randint(300, 800)
        
        if strategy == "nearest":
            # In nearest-worker, the same central workers get picked often
            # Let's heavily weight worker 0, 1, 2
            weights = [10, 8, 6, 2, 2, 1, 1]
            chosen = random.choices(range(num_workers), weights=weights, k=1)[0]
        else:
            # Equity graph prioritizes workers with lower earnings to maintain parity
            # We select the one with the lowest earnings (simplified equity index)
            chosen = np.argmin(worker_earnings)
            
        worker_earnings[chosen] += job_value
        
    return worker_earnings

def generate_chart():
    baseline_earnings = run_simulation("nearest")
    equity_earnings = run_simulation("equity")
    
    baseline_gini = calculate_gini(baseline_earnings)
    equity_gini = calculate_gini(equity_earnings)
    
    print(f"Nearest-Worker Gini: {baseline_gini:.3f}")
    print(f"Equity Index Gini: {equity_gini:.3f}")
    
    labels = ['Baseline (Nearest)', 'Equity Index']
    gini_values = [baseline_gini, equity_gini]
    
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(labels, gini_values, color=['#ef4444', '#10b981'])
    ax.set_ylabel('Gini Coefficient (Lower = More Equal)')
    ax.set_title('Earnings Inequality: Baseline vs Equity Index (200 Simulated Jobs)')
    ax.set_ylim(0, max(gini_values) * 1.2)
    
    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, yval + 0.01, f'{yval:.3f}', ha='center', va='bottom', fontweight='bold')
        
    plt.tight_layout()
    plt.savefig('equity_simulation_chart.png')
    print("Chart saved to equity_simulation_chart.png")

if __name__ == "__main__":
    generate_chart()
