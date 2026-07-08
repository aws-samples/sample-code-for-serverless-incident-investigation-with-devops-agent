#!/bin/bash
# Pre-validation script — runs the full demo workflow for both scenarios
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
PASS=0
FAIL=0

report() {
  local phase="$1" status="$2"
  if [ "$status" = "PASS" ]; then
    echo "  [PASS] $phase"
    PASS=$((PASS + 1))
  else
    echo "  [FAIL] $phase"
    FAIL=$((FAIL + 1))
  fi
}

echo "=== Pre-Validation: Full Demo Workflow ==="

# Scenario A: Code Bug
echo ""
echo "--- Scenario A: Code Bug ---"
./scripts/inject-code-bug.sh > /dev/null 2>&1 && report "Inject code bug" "PASS" || report "Inject code bug" "FAIL"
sleep 120
# Check alarm state
ALARM_STATE=$(aws cloudwatch describe-alarms --alarm-names "order-processing-error-rate-high" --region "$REGION" --query 'MetricAlarms[0].StateValue' --output text 2>/dev/null || echo "UNKNOWN")
[ "$ALARM_STATE" = "ALARM" ] && report "Alarm fired" "PASS" || report "Alarm fired" "FAIL"
./scripts/reset.sh > /dev/null 2>&1 && report "Reset after code bug" "PASS" || report "Reset after code bug" "FAIL"
sleep 30

# Scenario B: Infrastructure Issue
echo ""
echo "--- Scenario B: Infrastructure Issue ---"
./scripts/inject-infra-issue.sh > /dev/null 2>&1 && report "Inject infra issue" "PASS" || report "Inject infra issue" "FAIL"
sleep 120
ALARM_STATE=$(aws cloudwatch describe-alarms --alarm-names "order-processing-latency-p99-high" --region "$REGION" --query 'MetricAlarms[0].StateValue' --output text 2>/dev/null || echo "UNKNOWN")
[ "$ALARM_STATE" = "ALARM" ] && report "Alarm fired" "PASS" || report "Alarm fired" "FAIL"
./scripts/reset.sh > /dev/null 2>&1 && report "Reset after infra issue" "PASS" || report "Reset after infra issue" "FAIL"

echo ""
echo "=== Pre-Validation Report ==="
echo "PASS: $PASS | FAIL: $FAIL"
[ "$FAIL" -eq 0 ] && echo "STATUS: ALL PHASES PASSED" || echo "STATUS: SOME PHASES FAILED — review output above"
