#!/usr/bin/env bash
# run_case.sh <label> <extra ExecCmds>
#
# Runs one standalone measurement of the AnimBudget test map. The log lands in
# Saved/Logs/abt_<label>.log; the CSV goes to the engine user dir, not the project:
#   %LOCALAPPDATA%/UnrealEngine/5.8/Saved/Profiling/CSV/
#
# The MSYS_NO_PATHCONV exports matter: without them Git Bash rewrites the
# /Game/Maps/... argument into a Windows path and the map silently fails to load.
#
#   bash Scripts/AnimBudget/run_case.sh baseline "a.Budget.Enabled 0"
#   bash Scripts/AnimBudget/run_case.sh budget1 "a.Budget.Enabled 1, a.Budget.BudgetMs 1.0"
#
# Then summarise every capture in run order:
#   python Scripts/AnimBudget/analyze.py baseline budget1
set -u
export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL='*'

LABEL="$1"; shift
EXTRA="$*"

UE="${UE_ROOT:-/d/UE_5.8}/Engine/Binaries/Win64/UnrealEditor.exe"
PROJ="D:/UnrealEngineLab/UnrealEngineLab.uproject"
LOG="D:/UnrealEngineLab/Saved/Logs/abt_${LABEL}.log"

rm -f "$LOG"
"$UE" "$PROJ" /Game/Maps/AnimBudgetTest \
  -game -unattended -nosound -windowed -resx=640 -resy=360 \
  -ExitAfterCsvProfiling -csvCaptureFrames=1200 \
  -ExecCmds="t.MaxFPS 0, r.VSync 0, r.ScreenPercentage 50, ${EXTRA}" \
  -abslog="$LOG" > /dev/null 2>&1
echo "exit=$? label=${LABEL}"
