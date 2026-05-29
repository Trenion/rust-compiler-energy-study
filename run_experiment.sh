#!/bin/bash

# Configuration — adjust these paths to your actual locations
RAPL_MAIN="/home/guilherme/Desktop/RAPL_Measurements/RAPL/main"
PROJECT_DIR="/home/guilherme/Desktop/rust_compiler_evolution"

# Rust versions to test
VERSIONS=("1.0.0" "1.6.0" "1.14.0" "1.23.0" "1.32.0" "1.40.0" "1.49.0" "1.58.0" "1.67.0" "1.75.0" "1.84.0" "1.93.0" "stable")

mkdir -p results

cd "$PROJECT_DIR"

for VERSION in "${VERSIONS[@]}"; do
  echo "=========================================="
  echo "Testing with Rust version: $VERSION"
  echo "=========================================="
  
  # Switch to this compiler version
  rustup default "$VERSION"
  
  # Remove old binary if it exists
  rm -f mandelbrot
  
  # Compile (no --edition flag for compatibility with older Rust)
  rustc -C opt-level=3 -o mandelbrot mandelbrot.rs 2>&1
  
  if [ $? -ne 0 ]; then
    echo "Compilation failed for $VERSION, skipping..."
    continue
  fi
  
  # Run using the standard parametrized measurement mode
  # -powercap -1 means no power cap
  # -n_times 20 means run the benchmark 5 times
  # -variance 3 allows 3°C above baseline temperature
  # -time_out_limit 1 means timeout after 1 hour per run
  # -sleep_time 10 means 10 seconds idle before measuring
  sudo -E "$RAPL_MAIN" --standard \
    -command "./mandelbrot" \
    -language Rust \
    -program "mandelbrot_${VERSION}" \
    -n_times 20 \
    -variance 15 \
    -time_out_limit 1 \
    -sleep_time 20 \
    -powercap -1
  
  # The tool creates a CSV named after the program argument
  # Move it to results with version label
  if [ -f "mandelbrot_${VERSION}.csv" ]; then
    mv "mandelbrot_${VERSION}.csv" "/home/guilherme/Desktop/results"
  fi
  
  echo "Finished testing $VERSION"
  echo ""
done

echo "All tests complete. Results are in the 'results' directory."
