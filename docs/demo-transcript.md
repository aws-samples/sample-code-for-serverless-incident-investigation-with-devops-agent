# Known-Good Demo Transcript

This transcript documents a successful run of both demo scenarios for presenter reference.

## Scenario A: Code Bug

**Injection:** Ran `inject-code-bug.sh` — ECS service updated to v1.2.1-buggy image.

**Degradation observed:** POST /orders returns HTTP 500 within 30 seconds. GET /orders and /health continue working.

**Alarm fired:** `order-processing-error-rate-high` transitioned to ALARM after ~90 seconds.

**Agent investigation output (expected):**
- Consulted runbook: mapped "order-processing-service" to ECS service, log group, DynamoDB table
- CloudWatch Logs: Found `KeyError: 'delivery_address'` in `/ecs/order-processing-service`
- CloudWatch Metrics: 5xx error count spiked from 0 to 15+ per minute
- ECS deployment: Image tag changed from `v1.2.0` to `v1.2.1-buggy` at [timestamp]
- Root cause: Recent deployment introduced a KeyError in order_service.py — code accesses `data["delivery_address"]` but the correct key is `data["shipping_address"]`
- Resolution: Roll back ECS service to previous task definition (image v1.2.0), or fix the code to use the correct key

**Time to root cause:** ~2 minutes

**Recovery:** Ran `reset.sh` — service restored to v1.2.0, health check passing, alarm resolved.

---

## Scenario B: Infrastructure Issue

**Injection:** Ran `inject-infra-issue.sh` — CONNECTION_POOL_SIZE changed to 1, load generator ran for 30 seconds.

**Degradation observed:** All endpoints show elevated latency (>5s). Some requests timeout with 503/504.

**Alarm fired:** `order-processing-latency-p99-high` transitioned to ALARM after ~100 seconds.

**Agent investigation output (expected):**
- Consulted runbook: same resource mapping
- CloudWatch Logs: Found `ConnectionPoolTimeout` and `asyncio.TimeoutError` entries
- CloudWatch Metrics: p99 latency spiked from <200ms to >5s, healthy host count dropped
- ECS task definition: `CONNECTION_POOL_SIZE=1` (previously 10) — no image change
- Root cause: Environment variable `CONNECTION_POOL_SIZE` was changed from 10 to 1, causing connection pool exhaustion under concurrent load
- Resolution: Update ECS task definition to restore `CONNECTION_POOL_SIZE=10` and force new deployment

**Time to root cause:** ~2 minutes

**Recovery:** Ran `reset.sh` — CONNECTION_POOL_SIZE restored to 10, service healthy, alarm resolved.

---

## Scenario C: Cascading Failure

**Injection:** Ran `inject-cascading-failure.sh` — payment-records DynamoDB table capacity reduced to 1 RCU / 1 WCU, load generator ran 10 concurrent requests for 20 seconds against POST /orders.

**Degradation observed:** POST /orders returns HTTP 500 on >50% of requests within 30 seconds. GET /health continues returning 200. p99 latency on POST /orders exceeds 3 seconds.

**Alarm fired:** `order-processing-error-rate-high` transitioned to ALARM after ~90 seconds. `payment-records-throttle-alarm` transitioned to ALARM after ~60 seconds.

**Agent investigation output (expected):**
- Consulted runbook: mapped "order-processing-service" to Lambda function, log group, DynamoDB table, and discovered dependency on `payment-validation-service`
- CloudWatch Logs (order-processing-service): Found `PaymentValidationError` entries with `upstream_function: "payment-validation-service"` and shared `request_id` field
- CloudWatch Metrics (order-processing-service): 5xx error count spiked from 0 to 10+ per minute on POST /orders
- Traced to upstream dependency: `payment-validation-service` identified via `upstream_function` log field and service-mapping.json `dependencies` array
- CloudWatch Logs (payment-validation-service): Found `ProvisionedThroughputExceededException` entries with matching `request_id`, `table: "payment-records"`, `operation: "PutItem"`
- DynamoDB table configuration: `payment-records` table has provisioned capacity of 1 RCU / 1 WCU (expected baseline: 5/5)
- CloudTrail: Found `UpdateTable` API call on `payment-records` table reducing capacity from 5/5 to 1/1 at [timestamp]
- Root cause: The `payment-records` DynamoDB table capacity was reduced to 1/1, causing `ProvisionedThroughputExceededException` in the payment-validation-service, which cascades as HTTP 500 errors in the order-processing-service since it depends on payment validation before persisting orders
- Resolution: Restore `payment-records` table capacity to 5 RCU / 5 WCU via `aws dynamodb update-table`

**Time to root cause:** ~3 minutes (longer than Scenarios A/B due to cross-service tracing)

**Recovery:** Ran `reset.sh` — payment-records table capacity restored to 5/5, POST /orders returning 201, payment-records-throttle-alarm resolved, dashboard returning to healthy state.
