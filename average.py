import pandas as pd
import glob
import os

# Read all CSVs
files = glob.glob("results/mandelbrot_*.csv")
data = []

for f in files:
    # Extract version from filename
    version = os.path.basename(f).replace("mandelbrot_", "").replace(".csv", "")
    df = pd.read_csv(f)
    # Average the 20 runs
    avg = df[["Package", "Core", "GPU", "DRAM", "Time", "Temperature", "Memory"]].mean()
    avg["Version"] = version
    avg["Runs"] = len(df)
    data.append(avg)

# Combine and sort
summary = pd.DataFrame(data)
summary = summary.sort_values("Version")

print(summary.to_string(index=False))
summary.to_csv("summary_all_versions.csv", index=False)
