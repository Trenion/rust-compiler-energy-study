#!/usr/bin/env python3
"""
Energy and Performance Analysis across Rust Compiler Versions
Reads RAPL measurement CSVs and generates comparison graphs.
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import glob
import os
import re

# ============================================================
# CONFIGURATION — adjust these paths if needed
# ============================================================
RESULTS_DIR = "results"
OUTPUT_DIR = "graphs"

# Create output directory
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================
# 1. LOAD ALL CSV FILES
# ============================================================
csv_files = sorted(glob.glob(f"{RESULTS_DIR}/mandelbrot_*.csv"))

if not csv_files:
    print(f"No CSV files found in {RESULTS_DIR}/")
    print("Make sure your result files are named like: mandelbrot_1.8.0.csv")
    exit(1)

print(f"Found {len(csv_files)} CSV files")

all_data = []
for f in csv_files:
    # Extract version from filename
    basename = os.path.basename(f)
    version = basename.replace("mandelbrot_", "").replace(".csv", "")
    
    # Read the CSV
    df = pd.read_csv(f)
    
    # Strip whitespace from column names and string columns
    df.columns = df.columns.str.strip()
    for col in df.select_dtypes(include='object').columns:
        df[col] = df[col].str.strip()
    
    # Convert numeric columns
    numeric_cols = ["Package", "Core", "GPU", "DRAM", "Time", "Temperature", "Memory"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Add version column
    df["Version"] = version
    all_data.append(df)

# Combine all data
data = pd.concat(all_data, ignore_index=True)
print(f"Total measurements: {len(data)}")
print(f"Versions found: {sorted(data['Version'].unique())}")

# ============================================================
# 2. HANDLE VERSION SORTING
# ============================================================
def version_sort_key(ver):
    """Sort versions numerically: 1.8.0, 1.15.0, 1.23.0, ..., stable"""
    if ver == "stable":
        return (999, 999, 999)  # Put stable at the end
    parts = ver.split(".")
    return tuple(int(p) for p in parts)

# Sort versions
versions_sorted = sorted(data["Version"].unique(), key=version_sort_key)
# Create numeric x-axis positions
version_positions = list(range(len(versions_sorted)))

# ============================================================
# 3. COMPUTE AVERAGES PER VERSION
# ============================================================
metrics = ["Package", "Core", "GPU", "DRAM", "Time", "Temperature", "Memory"]

averages = {}
stderrs = {}
for version in versions_sorted:
    subset = data[data["Version"] == version]
    averages[version] = subset[metrics].mean()
    stderrs[version] = subset[metrics].std() / np.sqrt(len(subset))  # Standard error

summary_df = pd.DataFrame(averages).T
summary_df.index.name = "Version"
print("\n=== Summary Statistics ===")
print(summary_df.round(2).to_string())

# Save summary to CSV
summary_df.to_csv(f"{OUTPUT_DIR}/summary_table.csv")
print(f"\nSummary saved to {OUTPUT_DIR}/summary_table.csv")

# ============================================================
# 4. SET UP PLOT STYLE
# ============================================================
plt.style.use('seaborn-v0_8-darkgrid')
# Fallback if seaborn not available
try:
    plt.style.use('seaborn-v0_8-darkgrid')
except:
    plt.style.use('ggplot')

# Color palette
COLORS = {
    'Package': '#2196F3',  # Blue
    'Core': '#4CAF50',     # Green
    'GPU': '#FF9800',      # Orange
    'DRAM': '#9C27B0',     # Purple
    'Time': '#F44336',     # Red
}

# ============================================================
# 5. GRAPH 1: Energy Consumption (Package, Core, GPU, DRAM)
# ============================================================
fig, ax = plt.subplots(figsize=(12, 7))

energy_metrics = ["Package", "Core", "GPU", "DRAM"]
x = version_positions

for metric in energy_metrics:
    y = [averages[v][metric] for v in versions_sorted]
    err = [stderrs[v][metric] for v in versions_sorted]
    ax.errorbar(x, y, yerr=err, marker='o', linewidth=2, markersize=6,
                capsize=4, label=metric, color=COLORS[metric])

ax.set_xticks(x)
ax.set_xticklabels(versions_sorted, rotation=45, ha='right', fontsize=10)
ax.set_ylabel("Energy (Joules)", fontsize=12)
ax.set_xlabel("Rust Compiler Version", fontsize=12)
ax.set_title("Energy Consumption by Component Across Rust Compiler Versions", fontsize=14, fontweight='bold')
ax.legend(loc='upper right', fontsize=10)
ax.grid(True, alpha=0.3)

# Add value labels on the Package line (top energy consumer)
for i, v in enumerate(versions_sorted):
    val = averages[v]["Package"]
    ax.annotate(f'{val:.0f}', (x[i], val), textcoords="offset points",
                xytext=(0, 12), ha='center', fontsize=8, color=COLORS['Package'])

plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/energy_by_component.png", dpi=150, bbox_inches='tight')
plt.savefig(f"{OUTPUT_DIR}/energy_by_component.pdf", bbox_inches='tight')
print(f"Saved energy graph: {OUTPUT_DIR}/energy_by_component.png")
plt.close()

# ============================================================
# 6. GRAPH 2: Total Package Energy vs Version (Bar Chart)
# ============================================================
fig, ax = plt.subplots(figsize=(12, 6))

pkg_values = [averages[v]["Package"] for v in versions_sorted]
pkg_errors = [stderrs[v]["Package"] for v in versions_sorted]

bars = ax.bar(version_positions, pkg_values, yerr=pkg_errors, 
              capsize=5, color=COLORS['Package'], alpha=0.85, edgecolor='black', linewidth=0.5)

# Color the best and worst
best_idx = np.argmin(pkg_values)
worst_idx = np.argmax(pkg_values)
bars[best_idx].set_color('#4CAF50')   # Green for best
bars[worst_idx].set_color('#F44336')  # Red for worst

# Add percentage labels relative to baseline (first version)
baseline = pkg_values[0]
for i, (v, val) in enumerate(zip(versions_sorted, pkg_values)):
    pct = ((val - baseline) / baseline) * 100
    color = 'green' if pct < 0 else 'red'
    ax.annotate(f'{val:.1f}J\n({pct:+.1f}%)', (i, val), textcoords="offset points",
                xytext=(0, 10), ha='center', fontsize=8, color=color)

ax.set_xticks(version_positions)
ax.set_xticklabels(versions_sorted, rotation=45, ha='right', fontsize=10)
ax.set_ylabel("Package Energy (Joules)", fontsize=12)
ax.set_xlabel("Rust Compiler Version", fontsize=12)
ax.set_title("Total Package Energy Consumption Across Rust Versions\n(Green = Best, Red = Worst)", fontsize=14, fontweight='bold')
ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/package_energy_comparison.png", dpi=150, bbox_inches='tight')
plt.savefig(f"{OUTPUT_DIR}/package_energy_comparison.pdf", bbox_inches='tight')
print(f"Saved package energy graph: {OUTPUT_DIR}/package_energy_comparison.png")
plt.close()

# ============================================================
# 7. GRAPH 3: Execution Time vs Version
# ============================================================
fig, ax = plt.subplots(figsize=(12, 6))

time_values = [averages[v]["Time"] for v in versions_sorted]
time_errors = [stderrs[v]["Time"] for v in versions_sorted]

bars = ax.bar(version_positions, time_values, yerr=time_errors,
              capsize=5, color=COLORS['Time'], alpha=0.85, edgecolor='black', linewidth=0.5)

best_idx = np.argmin(time_values)
worst_idx = np.argmax(time_values)
bars[best_idx].set_color('#4CAF50')
bars[worst_idx].set_color('#F44336')

baseline = time_values[0]
for i, (v, val) in enumerate(zip(versions_sorted, time_values)):
    pct = ((val - baseline) / baseline) * 100
    color = 'green' if pct < 0 else 'red'
    ax.annotate(f'{val/1000:.2f}s\n({pct:+.1f}%)', (i, val), textcoords="offset points",
                xytext=(0, 10), ha='center', fontsize=8, color=color)

ax.set_xticks(version_positions)
ax.set_xticklabels(versions_sorted, rotation=45, ha='right', fontsize=10)
ax.set_ylabel("Execution Time (ms)", fontsize=12)
ax.set_xlabel("Rust Compiler Version", fontsize=12)
ax.set_title("Execution Time Across Rust Compiler Versions", fontsize=14, fontweight='bold')
ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/execution_time.png", dpi=150, bbox_inches='tight')
plt.savefig(f"{OUTPUT_DIR}/execution_time.pdf", bbox_inches='tight')
print(f"Saved execution time graph: {OUTPUT_DIR}/execution_time.png")
plt.close()

# ============================================================
# 8. GRAPH 4: Energy-Delay Product (EDP) - Combined Metric
# ============================================================
fig, ax = plt.subplots(figsize=(12, 6))

# EDP = Energy (Joules) × Time (seconds)
edp_values = []
edp_errors = []
for v in versions_sorted:
    pkg = averages[v]["Package"]  # Joules
    t = averages[v]["Time"] / 1000  # Convert ms to seconds
    edp = pkg * t
    edp_values.append(edp)
    
    # Propagate error for product
    pkg_err = stderrs[v]["Package"]
    t_err = stderrs[v]["Time"] / 1000
    edp_err = edp * np.sqrt((pkg_err/pkg)**2 + (t_err/t)**2)
    edp_errors.append(edp_err)

bars = ax.bar(version_positions, edp_values, yerr=edp_errors,
              capsize=5, color='#673AB7', alpha=0.85, edgecolor='black', linewidth=0.5)

best_idx = np.argmin(edp_values)
worst_idx = np.argmax(edp_values)
bars[best_idx].set_color('#4CAF50')
bars[worst_idx].set_color('#F44336')

baseline = edp_values[0]
for i, (v, val) in enumerate(zip(versions_sorted, edp_values)):
    pct = ((val - baseline) / baseline) * 100
    color = 'green' if pct < 0 else 'red'
    ax.annotate(f'{val:.0f}\n({pct:+.1f}%)', (i, val), textcoords="offset points",
                xytext=(0, 10), ha='center', fontsize=8, color=color)

ax.set_xticks(version_positions)
ax.set_xticklabels(versions_sorted, rotation=45, ha='right', fontsize=10)
ax.set_ylabel("Energy-Delay Product (J·s)", fontsize=12)
ax.set_xlabel("Rust Compiler Version", fontsize=12)
ax.set_title("Energy-Delay Product Across Rust Versions\n(Lower = Better: combines energy and time)", fontsize=14, fontweight='bold')
ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/energy_delay_product.png", dpi=150, bbox_inches='tight')
plt.savefig(f"{OUTPUT_DIR}/energy_delay_product.pdf", bbox_inches='tight')
print(f"Saved energy-delay product graph: {OUTPUT_DIR}/energy_delay_product.png")
plt.close()

# ============================================================
# 9. GRAPH 5: Performance per Watt (Package Energy vs Time Scatter)
# ============================================================
fig, ax = plt.subplots(figsize=(11, 7))

for i, v in enumerate(versions_sorted):
    pkg = averages[v]["Package"]
    t = averages[v]["Time"] / 1000  # seconds
    ax.scatter(t, pkg, s=200, label=v, zorder=5)
    ax.annotate(v, (t, pkg), textcoords="offset points",
                xytext=(8, 5), fontsize=8, alpha=0.8)

ax.set_xlabel("Execution Time (seconds)", fontsize=12)
ax.set_ylabel("Package Energy (Joules)", fontsize=12)
ax.set_title("Performance per Watt: Energy vs Time Across Rust Versions\n(Lower and further left = better)", fontsize=14, fontweight='bold')
ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=8)
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/performance_per_watt.png", dpi=150, bbox_inches='tight')
plt.savefig(f"{OUTPUT_DIR}/performance_per_watt.pdf", bbox_inches='tight')
print(f"Saved performance-per-watt graph: {OUTPUT_DIR}/performance_per_watt.png")
plt.close()

# ============================================================
# 10. GRAPH 6: Combined Dashboard (Subplots)
# ============================================================
fig, axes = plt.subplots(2, 2, figsize=(14, 12))
fig.suptitle("Rust Compiler Evolution: Energy and Performance Analysis", fontsize=16, fontweight='bold')

# Subplot 1: Package Energy
ax = axes[0, 0]
pkg_vals = [averages[v]["Package"] for v in versions_sorted]
ax.bar(version_positions, pkg_vals, color=COLORS['Package'], alpha=0.8, edgecolor='black', linewidth=0.5)
ax.set_xticks(version_positions)
ax.set_xticklabels(versions_sorted, rotation=45, ha='right', fontsize=8)
ax.set_ylabel("Joules", fontsize=11)
ax.set_title("Package Energy", fontsize=12, fontweight='bold')
ax.grid(axis='y', alpha=0.3)

# Subplot 2: Execution Time
ax = axes[0, 1]
time_vals = [averages[v]["Time"] / 1000 for v in versions_sorted]
ax.bar(version_positions, time_vals, color=COLORS['Time'], alpha=0.8, edgecolor='black', linewidth=0.5)
ax.set_xticks(version_positions)
ax.set_xticklabels(versions_sorted, rotation=45, ha='right', fontsize=8)
ax.set_ylabel("Seconds", fontsize=11)
ax.set_title("Execution Time", fontsize=12, fontweight='bold')
ax.grid(axis='y', alpha=0.3)

# Subplot 3: Energy-Delay Product
ax = axes[1, 0]
ax.bar(version_positions, edp_values, color='#673AB7', alpha=0.8, edgecolor='black', linewidth=0.5)
ax.set_xticks(version_positions)
ax.set_xticklabels(versions_sorted, rotation=45, ha='right', fontsize=8)
ax.set_ylabel("J·s", fontsize=11)
ax.set_title("Energy-Delay Product", fontsize=12, fontweight='bold')
ax.grid(axis='y', alpha=0.3)

# Subplot 4: DRAM Energy (stability check)
ax = axes[1, 1]
dram_vals = [averages[v]["DRAM"] for v in versions_sorted]
ax.bar(version_positions, dram_vals, color=COLORS['DRAM'], alpha=0.8, edgecolor='black', linewidth=0.5)
ax.set_xticks(version_positions)
ax.set_xticklabels(versions_sorted, rotation=45, ha='right', fontsize=8)
ax.set_ylabel("Joules", fontsize=11)
ax.set_title("DRAM Energy", fontsize=12, fontweight='bold')
ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/dashboard.png", dpi=150, bbox_inches='tight')
plt.savefig(f"{OUTPUT_DIR}/dashboard.pdf", bbox_inches='tight')
print(f"Saved dashboard: {OUTPUT_DIR}/dashboard.png")
plt.close()

# ============================================================
# 11. PRINT INSIGHTS
# ============================================================
print("\n" + "="*60)
print("KEY INSIGHTS FOR YOUR REPORT")
print("="*60)

best_energy = versions_sorted[np.argmin(pkg_vals)]
worst_energy = versions_sorted[np.argmax(pkg_vals)]
best_time = versions_sorted[np.argmin(time_values)]
worst_time = versions_sorted[np.argmax(time_values)]
best_edp = versions_sorted[np.argmin(edp_values)]

print(f"Best energy efficiency: Rust {best_energy} ({min(pkg_vals):.1f} Joules)")
print(f"Worst energy efficiency: Rust {worst_energy} ({max(pkg_vals):.1f} Joules)")
print(f"Best execution time: Rust {best_time} ({min(time_values)/1000:.2f} seconds)")
print(f"Worst execution time: Rust {worst_time} ({max(time_values)/1000:.2f} seconds)")
print(f"Best EDP (combined metric): Rust {best_edp}")

improvement = ((pkg_vals[-1] - pkg_vals[0]) / pkg_vals[0]) * 100
direction = "improvement" if improvement < 0 else "increase"
print(f"\nEnergy change from {versions_sorted[0]} to {versions_sorted[-1]}: {improvement:+.1f}% ({direction})")

time_improvement = ((time_values[-1] - time_values[0]) / time_values[0]) * 100
time_direction = "improvement" if time_improvement < 0 else "increase"
print(f"Time change from {versions_sorted[0]} to {versions_sorted[-1]}: {time_improvement:+.1f}% ({time_direction})")

print(f"\nAll graphs saved to: {OUTPUT_DIR}/")
print("Files: energy_by_component.png, package_energy_comparison.png, execution_time.png,")
print("       energy_delay_product.png, performance_per_watt.png, dashboard.png")

# ============================================================
# 12. GRAPH 7: Speedup (relative to baseline version)
# ============================================================
fig, ax = plt.subplots(figsize=(12, 7))

baseline_version = versions_sorted[0]  # Use earliest version as baseline
baseline_time = averages[baseline_version]["Time"]

speedup_values = []
for v in versions_sorted:
    t = averages[v]["Time"]
    speedup = baseline_time / t  # Speedup = T_baseline / T_current
    speedup_values.append(speedup)

# Bar chart
colors_speedup = []
for val in speedup_values:
    if val >= 1.0:
        colors_speedup.append('#4CAF50')  # Green for speedup (faster)
    else:
        colors_speedup.append('#F44336')  # Red for slowdown

bars = ax.bar(version_positions, speedup_values, color=colors_speedup, 
              alpha=0.85, edgecolor='black', linewidth=0.5)

# Add reference line at 1.0 (no change)
ax.axhline(y=1.0, color='black', linestyle='--', linewidth=1, alpha=0.7, label='Baseline (no change)')

# Add value labels
for i, (v, val) in enumerate(zip(versions_sorted, speedup_values)):
    label = f'{val:.3f}x'
    ax.annotate(label, (i, val), textcoords="offset points",
                xytext=(0, 10), ha='center', fontsize=9, fontweight='bold',
                color=colors_speedup[i])

ax.set_xticks(version_positions)
ax.set_xticklabels(versions_sorted, rotation=45, ha='right', fontsize=10)
ax.set_ylabel(f"Speedup (relative to Rust {baseline_version})", fontsize=12)
ax.set_xlabel("Rust Compiler Version", fontsize=12)
ax.set_title(f"Speedup Across Rust Compiler Versions\n(Baseline: Rust {baseline_version}, >1.0 = faster, <1.0 = slower)", 
             fontsize=14, fontweight='bold')
ax.legend(fontsize=10)
ax.grid(axis='y', alpha=0.3)

# Adjust y-axis to show meaningful range
ymin = min(speedup_values) * 0.95
ymax = max(speedup_values) * 1.05
ax.set_ylim(ymin, ymax)

plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/speedup.png", dpi=150, bbox_inches='tight')
plt.savefig(f"{OUTPUT_DIR}/speedup.pdf", bbox_inches='tight')
print(f"Saved speedup graph: {OUTPUT_DIR}/speedup.png")
plt.close()


# ============================================================
# 13. GRAPH 8: Greenup (energy efficiency relative to baseline)
# ============================================================
fig, ax = plt.subplots(figsize=(12, 7))

baseline_energy = averages[baseline_version]["Package"]

greenup_values = []
for v in versions_sorted:
    e = averages[v]["Package"]
    greenup = baseline_energy / e  # Greenup = E_baseline / E_current
    greenup_values.append(greenup)

# Bar chart
colors_greenup = []
for val in greenup_values:
    if val >= 1.0:
        colors_greenup.append('#2196F3')  # Blue for energy improvement (greener)
    else:
        colors_greenup.append('#FF9800')  # Orange for energy regression

bars = ax.bar(version_positions, greenup_values, color=colors_greenup,
              alpha=0.85, edgecolor='black', linewidth=0.5)

# Add reference line at 1.0
ax.axhline(y=1.0, color='black', linestyle='--', linewidth=1, alpha=0.7, label='Baseline (no change)')

# Add value labels
for i, (v, val) in enumerate(zip(versions_sorted, greenup_values)):
    label = f'{val:.3f}x'
    ax.annotate(label, (i, val), textcoords="offset points",
                xytext=(0, 10), ha='center', fontsize=9, fontweight='bold',
                color=colors_greenup[i])

ax.set_xticks(version_positions)
ax.set_xticklabels(versions_sorted, rotation=45, ha='right', fontsize=10)
ax.set_ylabel(f"Greenup (relative to Rust {baseline_version})", fontsize=12)
ax.set_xlabel("Rust Compiler Version", fontsize=12)
ax.set_title(f"Greenup (Energy Efficiency) Across Rust Compiler Versions\n(Baseline: Rust {baseline_version}, >1.0 = more efficient, <1.0 = less efficient)",
             fontsize=14, fontweight='bold')
ax.legend(fontsize=10)
ax.grid(axis='y', alpha=0.3)

ymin = min(greenup_values) * 0.95
ymax = max(greenup_values) * 1.05
ax.set_ylim(ymin, ymax)

plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/greenup.png", dpi=150, bbox_inches='tight')
plt.savefig(f"{OUTPUT_DIR}/greenup.pdf", bbox_inches='tight')
print(f"Saved greenup graph: {OUTPUT_DIR}/greenup.png")
plt.close()


# ============================================================
# 14. GRAPH 9: Powerup (average power consumption relative to baseline)
# ============================================================
fig, ax = plt.subplots(figsize=(12, 7))

# Average Power = Energy / Time  (Watts = Joules / Seconds)
baseline_power = baseline_energy / (baseline_time / 1000)  # Convert ms to seconds

powerup_values = []
power_values_watts = []
for v in versions_sorted:
    e = averages[v]["Package"]        # Joules
    t = averages[v]["Time"] / 1000    # Seconds
    power = e / t                      # Watts
    power_values_watts.append(power)
    powerup = baseline_power / power   # Powerup = P_baseline / P_current
    powerup_values.append(powerup)

# Bar chart
colors_powerup = []
for val in powerup_values:
    if val >= 1.0:
        colors_powerup.append('#9C27B0')  # Purple for lower power (better)
    else:
        colors_powerup.append('#F44336')  # Red for higher power (worse)

bars = ax.bar(version_positions, powerup_values, color=colors_powerup,
              alpha=0.85, edgecolor='black', linewidth=0.5)

# Add reference line at 1.0
ax.axhline(y=1.0, color='black', linestyle='--', linewidth=1, alpha=0.7, label='Baseline (no change)')

# Add value labels (show both powerup ratio and actual watts)
for i, (v, val, watts) in enumerate(zip(versions_sorted, powerup_values, power_values_watts)):
    label = f'{val:.3f}x\n({watts:.1f}W)'
    ax.annotate(label, (i, val), textcoords="offset points",
                xytext=(0, 14), ha='center', fontsize=8, fontweight='bold',
                color=colors_powerup[i])

ax.set_xticks(version_positions)
ax.set_xticklabels(versions_sorted, rotation=45, ha='right', fontsize=10)
ax.set_ylabel(f"Powerup (relative to Rust {baseline_version})", fontsize=12)
ax.set_xlabel("Rust Compiler Version", fontsize=12)
ax.set_title(f"Powerup (Average Power Efficiency) Across Rust Compiler Versions\n(Baseline: Rust {baseline_version}, >1.0 = lower avg power, <1.0 = higher avg power)",
             fontsize=14, fontweight='bold')
ax.legend(fontsize=10)
ax.grid(axis='y', alpha=0.3)

ymin = min(powerup_values) * 0.95
ymax = max(powerup_values) * 1.05
ax.set_ylim(ymin, ymax)

plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/powerup.png", dpi=150, bbox_inches='tight')
plt.savefig(f"{OUTPUT_DIR}/powerup.pdf", bbox_inches='tight')
print(f"Saved powerup graph: {OUTPUT_DIR}/powerup.png")
plt.close()


# ============================================================
# 15. GRAPH 10: Combined Speedup-Greenup-Powerup Dashboard
# ============================================================
fig, axes = plt.subplots(1, 3, figsize=(18, 6))
fig.suptitle("Rust Compiler Evolution: Speedup, Greenup, and Powerup Analysis", 
             fontsize=16, fontweight='bold')

# Speedup subplot
ax = axes[0]
colors_s = ['#4CAF50' if v >= 1.0 else '#F44336' for v in speedup_values]
ax.bar(version_positions, speedup_values, color=colors_s, alpha=0.85, edgecolor='black', linewidth=0.5)
ax.axhline(y=1.0, color='black', linestyle='--', linewidth=0.8, alpha=0.5)
ax.set_xticks(version_positions)
ax.set_xticklabels(versions_sorted, rotation=90, ha='center', fontsize=7)
ax.set_ylabel("Speedup (×)", fontsize=11)
ax.set_title("Speedup", fontsize=12, fontweight='bold')
ax.grid(axis='y', alpha=0.3)

# Greenup subplot
ax = axes[1]
colors_g = ['#2196F3' if v >= 1.0 else '#FF9800' for v in greenup_values]
ax.bar(version_positions, greenup_values, color=colors_g, alpha=0.85, edgecolor='black', linewidth=0.5)
ax.axhline(y=1.0, color='black', linestyle='--', linewidth=0.8, alpha=0.5)
ax.set_xticks(version_positions)
ax.set_xticklabels(versions_sorted, rotation=90, ha='center', fontsize=7)
ax.set_ylabel("Greenup (×)", fontsize=11)
ax.set_title("Greenup", fontsize=12, fontweight='bold')
ax.grid(axis='y', alpha=0.3)

# Powerup subplot
ax = axes[2]
colors_p = ['#9C27B0' if v >= 1.0 else '#F44336' for v in powerup_values]
ax.bar(version_positions, powerup_values, color=colors_p, alpha=0.85, edgecolor='black', linewidth=0.5)
ax.axhline(y=1.0, color='black', linestyle='--', linewidth=0.8, alpha=0.5)
ax.set_xticks(version_positions)
ax.set_xticklabels(versions_sorted, rotation=90, ha='center', fontsize=7)
ax.set_ylabel("Powerup (×)", fontsize=11)
ax.set_title("Powerup", fontsize=12, fontweight='bold')
ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/speedup_greenup_powerup_dashboard.png", dpi=150, bbox_inches='tight')
plt.savefig(f"{OUTPUT_DIR}/speedup_greenup_powerup_dashboard.pdf", bbox_inches='tight')
print(f"Saved combined dashboard: {OUTPUT_DIR}/speedup_greenup_powerup_dashboard.png")
plt.close()
