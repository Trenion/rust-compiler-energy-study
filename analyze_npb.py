#!/usr/bin/env python3
"""
NPB-Rust Energy Analysis Script
Reads all NPB CSV files and produces summary statistics and graphs.
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import glob
import os
import re

# ============================================================
# CONFIGURATION
# ============================================================
RESULTS_DIR = "/home/guilherme/Desktop/NPB-Rust/npb_all_results_class_W"  # <-- adjust
OUTPUT_DIR = "/home/guilherme/Desktop/graphs/npb_graphs_W"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================
# 1. LOAD ALL CSV FILES
# ============================================================
csv_files = sorted(glob.glob(f"{RESULTS_DIR}/NPB_*.csv"))

if not csv_files:
    print(f"No CSV files found in {RESULTS_DIR}/")
    exit(1)

print(f"Found {len(csv_files)} CSV files")

all_data = []
for f in csv_files:
    basename = os.path.basename(f).replace(".csv", "")
    # Parse filename: NPB_<program>_<class>_<version>.csv
    parts = basename.split("_")
    # parts = ["NPB", "ep", "A", "1.85.0"]
    program = parts[1]
    cls = parts[2]
    version = parts[3]
    
    df = pd.read_csv(f)
    df.columns = df.columns.str.strip()
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].str.strip()
    
    numeric_cols = ["Package", "Core", "GPU", "DRAM", "Time", "Temperature", "Memory"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df["Program"] = program
    df["Class"] = cls
    df["Version"] = version
    all_data.append(df)

data = pd.concat(all_data, ignore_index=True)
print(f"Total measurements: {len(data)}")
print(f"Programs: {sorted(data['Program'].unique())}")
print(f"Versions: {sorted(data['Version'].unique())}")

# ============================================================
# 2. COMPUTE AVERAGES PER PROGRAM AND VERSION
# ============================================================
metrics = ["Package", "Core", "GPU", "DRAM", "Time", "Temperature", "Memory"]

summary = data.groupby(["Program", "Version"])[metrics].mean().round(2)
summary["Runs"] = data.groupby(["Program", "Version"]).size()

print("\n=== Summary Statistics ===")
print(summary.to_string())

# Save summary
summary.to_csv(f"{OUTPUT_DIR}/npb_summary.csv")
print(f"\nSummary saved to {OUTPUT_DIR}/npb_summary.csv")

# ============================================================
# 3. GRAPH: Package Energy per Program
# ============================================================
programs = sorted(data["Program"].unique())
versions = sorted(data["Version"].unique())

fig, axes = plt.subplots(2, 4, figsize=(20, 10))
axes = axes.flatten()

for idx, prog in enumerate(programs):
    ax = axes[idx]
    prog_data = data[data["Program"] == prog]
    
    x = range(len(versions))
    means = []
    errs = []
    for v in versions:
        subset = prog_data[prog_data["Version"] == v]
        means.append(subset["Package"].mean())
        errs.append(subset["Package"].std() / np.sqrt(len(subset)))
    
    ax.bar(x, means, yerr=errs, capsize=5, color='steelblue', edgecolor='black')
    ax.set_xticks(x)
    ax.set_xticklabels(versions, rotation=45, ha='right', fontsize=8)
    ax.set_title(f"{prog.upper()} - Package Energy", fontsize=11, fontweight='bold')
    ax.set_ylabel("Joules")
    ax.grid(axis='y', alpha=0.3)

# Hide unused subplots if fewer than 8 programs
for idx in range(len(programs), len(axes)):
    axes[idx].set_visible(False)

plt.suptitle("Package Energy by NPB Program and Rust Version (Class A)", fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/npb_package_energy.png", dpi=150, bbox_inches='tight')
plt.close()
print(f"Saved: {OUTPUT_DIR}/npb_package_energy.png")

# ============================================================
# 4. GRAPH: Execution Time per Program
# ============================================================
fig, axes = plt.subplots(2, 4, figsize=(20, 10))
axes = axes.flatten()

for idx, prog in enumerate(programs):
    ax = axes[idx]
    prog_data = data[data["Program"] == prog]
    
    x = range(len(versions))
    means = []
    errs = []
    for v in versions:
        subset = prog_data[prog_data["Version"] == v]
        means.append(subset["Time"].mean() / 1000)  # Convert to seconds
        errs.append(subset["Time"].std() / np.sqrt(len(subset)) / 1000)
    
    ax.bar(x, means, yerr=errs, capsize=5, color='coral', edgecolor='black')
    ax.set_xticks(x)
    ax.set_xticklabels(versions, rotation=45, ha='right', fontsize=8)
    ax.set_title(f"{prog.upper()} - Execution Time", fontsize=11, fontweight='bold')
    ax.set_ylabel("Seconds")
    ax.grid(axis='y', alpha=0.3)

for idx in range(len(programs), len(axes)):
    axes[idx].set_visible(False)

plt.suptitle("Execution Time by NPB Program and Rust Version (Class A)", fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/npb_execution_time.png", dpi=150, bbox_inches='tight')
plt.close()
print(f"Saved: {OUTPUT_DIR}/npb_execution_time.png")

# ============================================================
# 5. GRAPH: Greenup per Program (relative to 1.85.0)
# ============================================================
fig, axes = plt.subplots(2, 4, figsize=(20, 10))
axes = axes.flatten()
baseline_version = versions[0]  # 1.85.0

for idx, prog in enumerate(programs):
    ax = axes[idx]
    prog_data = data[data["Program"] == prog]
    
    baseline_energy = prog_data[prog_data["Version"] == baseline_version]["Package"].mean()
    
    greenup_values = []
    for v in versions:
        energy = prog_data[prog_data["Version"] == v]["Package"].mean()
        greenup = baseline_energy / energy
        greenup_values.append(greenup)
    
    colors = ['#4CAF50' if g >= 1.0 else '#F44336' for g in greenup_values]
    x = range(len(versions))
    ax.bar(x, greenup_values, color=colors, edgecolor='black')
    ax.axhline(y=1.0, color='black', linestyle='--', linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(versions, rotation=45, ha='right', fontsize=8)
    ax.set_title(f"{prog.upper()} - Greenup", fontsize=11, fontweight='bold')
    ax.set_ylabel("Greenup (×)")
    ax.grid(axis='y', alpha=0.3)
    
    # Add value labels
    for i, val in enumerate(greenup_values):
        ax.text(i, val + 0.01, f'{val:.3f}', ha='center', fontsize=7)

for idx in range(len(programs), len(axes)):
    axes[idx].set_visible(False)

plt.suptitle(f"Greenup by NPB Program (Baseline: Rust {baseline_version})", fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/npb_greenup.png", dpi=150, bbox_inches='tight')
plt.close()
print(f"Saved: {OUTPUT_DIR}/npb_greenup.png")

# ============================================================
# 6. PRINT KEY FINDINGS
# ============================================================
print("\n" + "="*60)
print("KEY FINDINGS PER PROGRAM")
print("="*60)

for prog in programs:
    prog_data = data[data["Program"] == prog]
    e_first = prog_data[prog_data["Version"] == versions[0]]["Package"].mean()
    e_last = prog_data[prog_data["Version"] == versions[-1]]["Package"].mean()
    change = ((e_last - e_first) / e_first) * 100
    
    t_first = prog_data[prog_data["Version"] == versions[0]]["Time"].mean()
    t_last = prog_data[prog_data["Version"] == versions[-1]]["Time"].mean()
    t_change = ((t_last - t_first) / t_first) * 100
    
    print(f"\n{prog.upper()}:")
    print(f"  Energy: {e_first:.1f} J -> {e_last:.1f} J ({change:+.1f}%)")
    print(f"  Time:   {t_first/1000:.2f} s -> {t_last/1000:.2f} s ({t_change:+.1f}%)")
