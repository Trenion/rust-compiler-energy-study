#!/bin/bash

# ==============================================
#  NPB-Rust Full Energy Measurement Script
#  All 8 kernels/applications, 20 runs each
#  Rust versions: 1.85.0, 1.90.0, stable
# ==============================================

# ---------- Configuration ----------
RAPL_MAIN="/home/guilherme/Desktop/RAPL_Measurements/RAPL/main"
NPB_DIR="/home/guilherme/Desktop/NPB-Rust/NPB-RUST"   # <-- note the subfolder
RESULTS_DIR="/home/guilherme/Desktop/NPB-Rust/npb_all_results_class_A"
VERSIONS=("1.85.0" "1.90.0" "stable")
PROGRAMS=("ep" "ft" "cg" "is" "mg" "bt" "sp" "lu")
CLASS="A"            # <-- Problem class: S, W, A, B, C, D, E

N_TIMES=20
VARIANCE=15
TIME_OUT_LIMIT=4       # hours (increased for Class A)
SLEEP_TIME=20
POWERCAP=-1

# ---------- Setup ----------
mkdir -p "$RESULTS_DIR"
cd "$NPB_DIR" || { echo "ERROR: cannot cd to $NPB_DIR"; exit 1; }

# ---------- Main Loop ----------
for VERSION in "${VERSIONS[@]}"; do
  echo "=========================================="
  echo "Testing with Rust version: $VERSION"
  echo "=========================================="

  rustup default "$VERSION"

  for PROG in "${PROGRAMS[@]}"; do
    echo "--------------------------------------------------"
    echo "  Building $PROG (Class $CLASS) with Rust $VERSION"
    echo "--------------------------------------------------"

    cargo clean 2>&1 >/dev/null

    # Build with class flag
    RUSTFLAGS="--cfg class=\"$CLASS\"" cargo build --release --bin "$PROG" 2>&1

    if [ $? -ne 0 ]; then
      echo "  ERROR: Build failed for $PROG (Rust $VERSION), skipping..."
      continue
    fi

    BIN="$NPB_DIR/target/release/$PROG"
    if [ ! -f "$BIN" ]; then
      echo "  ERROR: Binary not found: $BIN"
      continue
    fi

    echo "  -> Measuring $PROG ($N_TIMES runs, Class $CLASS)..."

    sudo -E "$RAPL_MAIN" --standard \
      -command "$BIN" \
      -language Rust \
      -program "NPB_${PROG}_${CLASS}_${VERSION}" \
      -n_times $N_TIMES \
      -variance $VARIANCE \
      -time_out_limit $TIME_OUT_LIMIT \
      -sleep_time $SLEEP_TIME \
      -powercap $POWERCAP

    # Move CSV to results folder
    CSV_FILE="$NPB_DIR/NPB_${PROG}_${CLASS}_${VERSION}.csv"
    if [ -f "$CSV_FILE" ]; then
      mv "$CSV_FILE" "$RESULTS_DIR/"
      echo "    Saved: $RESULTS_DIR/NPB_${PROG}_${CLASS}_${VERSION}.csv"
    else
      echo "  WARNING: CSV not generated for $PROG (Rust $VERSION)"
    fi
  done
done

echo ""
echo "All NPB tests completed. Results in: $RESULTS_DIR"
echo "Expected files: $((${#VERSIONS[@]} * ${#PROGRAMS[@]}))"
