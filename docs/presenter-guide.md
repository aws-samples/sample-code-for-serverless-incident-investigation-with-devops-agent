# Presenter Guide: DevOps Agent Customer Demo

## Event Title
**AWS DevOps Agent: Watch AI Investigate a Live Incident — Live Demo & Q&A**

## Duration: 35-40 minutes

---

## Pre-Demo Checklist

- [ ] AWS credentials configured (`aws sts get-caller-identity` → your demo account)
- [ ] Stack deployed (`aws cloudformation describe-stacks --stack-name devops-agent-demo`)
- [ ] Health check passing: `curl https://<your-api-id>.execute-api.us-east-1.amazonaws.com/health`
- [ ] Dashboard opens: `open demo-app/dashboard/index.html`
- [ ] DevOps Agent space configured with webhook
- [ ] Reset script tested: `bash demo-app/scripts/reset.sh`
- [ ] Browser tabs ready: Dashboard, DevOps Agent console, AWS Console (CloudWatch)

---

## Agenda

| Time | Phase | What happens |
|------|-------|--------------|
| 0-5 min | Intro & Context | Why DevOps Agent, the problem it solves |
| 5-8 min | Show healthy app | Dashboard green, place orders, everything works |
| 8-12 min | Inject throttling | Set concurrency to 1, burst test shows failures |
| 12-15 min | Fire webhook | Trigger DevOps Agent investigation |
| 15-28 min | Agent investigates | Watch live in console — the main event |
| 28-33 min | Reset & recap | Fix the issue, show recovery, key takeaways |
| 33-40 min | Q&A | |

---

## Phase 1: Intro & Context (5 minutes)

**Talking points:**
- "When production breaks at 2am, your team spends 30-60 minutes correlating logs, checking deployments, and tracing through code. What if an AI agent could do that investigation autonomously?"
- "Today we'll break a real service, fire an alert, and watch AWS DevOps Agent investigate — no human intervention."
- "The scenario: a configuration change causes our order service to fail under load. This is the kind of issue that tests won't catch — it only manifests in production under real traffic."

---

## Phase 2: Show Healthy App (3 minutes)

**What to do:** Open the dashboard. Show everything is green.

1. Open `demo-app/dashboard/index.html` in browser
2. Click "Place New Order" a few times — all succeed
3. Click "Burst Test (10 concurrent)" — all succeed
4. Point out: status badge is green, zero errors, low latency

**Talking point:** "This is our order processing service — Lambda, API Gateway, DynamoDB. The dashboard shows real-time health. Everything is green. Orders are flowing."

---

## Phase 3: Inject Throttling (4 minutes)

**What to do:** Run the injection script. Show the dashboard go red.

```bash
bash demo-app/scripts/inject-throttling.sh
```

**What this does:** Sets Lambda reserved concurrency to 1. Only one request can execute at a time — all concurrent requests get throttled.

**After injection:**
1. Click "Burst Test (10 concurrent)" on the dashboard
2. Watch 8-9 out of 10 requests fail (500 errors in activity log)
3. Status badge flips to DEGRADED or SERVICE DOWN

**Talking points:**
- "Someone just changed a configuration — set the Lambda concurrency to 1. Maybe it was a cost optimization attempt, maybe a misconfigured Terraform variable."
- "Single requests still work fine. But under any real traffic, the service falls over."
- "This is the kind of issue that's invisible in testing — it only manifests under concurrent load in production."
- "Notice: the code didn't change. Tests would pass. Health checks pass on single requests. But customers are experiencing failures."

---

## Phase 4: Fire Webhook (2 minutes)

**What to do:** Send the alert to DevOps Agent.

```bash
python3 demo-app/scripts/simulate_webhook.py --scenario throttling
```

**Talking point:** "In production, this webhook would fire automatically from your monitoring tool — PagerDuty, Datadog, CloudWatch Alarm via SNS. We're simulating that trigger now."

Show the DevOps Agent console — the investigation should start appearing.

---

## Phase 5: Agent Investigates (13 minutes)

**What to do:** Switch to the DevOps Agent console. Watch and narrate.

**What the agent should do:**
1. Receive the alert — "Lambda throttling detected"
2. Check CloudWatch metrics — see Throttles metric spiking
3. Check Lambda configuration — find reserved concurrency = 1
4. Check CloudTrail — find who/what changed the concurrency setting
5. Correlate timeline — concurrency changed at X, throttling started at X
6. Root cause: "Reserved concurrency set to 1, causing all concurrent requests to be throttled"
7. Recommend fix: "Remove reserved concurrency limit or increase to appropriate value"

**Narration while agent works:**
- "It's pulling CloudWatch metrics now — looking at the Throttles metric..."
- "Now it's checking the Lambda function configuration..."
- "It found it — reserved concurrency is set to 1. That's the bottleneck."
- "It's checking CloudTrail to see when this change was made..."
- "Root cause identified: configuration change, not a code bug. This is why tests didn't catch it."

**Key talking point:** "Notice what the agent did: it checked the code (no changes), checked deployments (no new deploy), then looked at configuration — and found the concurrency limit. A human would follow the same investigation path, but it takes 15-30 minutes of clicking through consoles. The agent did it in minutes."

---

## Phase 6: Reset & Recap (5 minutes)

**What to do:** Fix the issue, show recovery.

```bash
bash demo-app/scripts/reset.sh
```

Refresh dashboard — show it going green again. Click "Burst Test" — all succeed.

**Key takeaways:**
1. "DevOps Agent investigates autonomously — from alert to root cause without human intervention"
2. "It works with your existing AWS infrastructure — CloudWatch, Lambda, CloudTrail. No new agents to install."
3. "The investigation pattern works for code bugs, config issues, infrastructure problems — anything that leaves traces in your AWS environment"
4. "Integration is simple: webhook from your monitoring tool → agent investigates → surfaces root cause"

---

## Phase 7: Q&A (7 minutes)

**Common questions to prepare for:**

| Question | Answer |
|----------|--------|
| "How does it integrate with Datadog/PagerDuty?" | Native integrations via webhook + MCP. Datadog/Splunk/Grafana can both trigger investigations and provide telemetry. |
| "Does it have write access to fix things?" | Currently read-only investigation. It recommends fixes but doesn't auto-remediate (yet). |
| "What about multi-account?" | Supports cross-account monitoring via IAM roles. |
| "Pricing?" | 2-month free trial. Then per-investigation pricing. |
| "How long do investigations take?" | Typically 2-5 minutes depending on complexity. |
| "Can it access our code repos?" | Yes — GitHub, GitLab, Azure DevOps integrations available. |

---

## Alternative Scenario: Cascading Failure (Advanced)

This scenario is architecturally more complex than the throttling scenario above. The alert fires on the **order-processing-service** (Service A), but the root cause is in the **payment-validation-service** (Service B). The DevOps Agent must trace across service boundaries using dependency mapping to find the true root cause.

### Key Talking Point

> "This is the hardest class of incident to debug: the alert fires on Service A, but the root cause is in Service B. The agent has to trace across service boundaries using the dependency mapping — exactly what takes humans 30-60 minutes of clicking through multiple consoles."

### Phase-by-Phase Timeline

| Time | Phase | What happens |
|------|-------|--------------|
| 0-2 min | Inject cascading failure | Reduce payment-records DynamoDB capacity, generate load |
| 2-4 min | Observe degradation | Dashboard shows order service errors, payment service throttling |
| 4-5 min | Fire webhook | Trigger DevOps Agent with alert on order-processing-service |
| 5-18 min | Agent investigates | Agent traces from order service → payment service → DynamoDB root cause |
| 18-22 min | Reset & recap | Restore capacity, show recovery, discuss cross-service correlation |

### Phase C1: Inject Cascading Failure (2 minutes)

**What to do:** Run the cascading failure injection script.

```bash
bash demo-app/scripts/inject-cascading-failure.sh
```

**What this does:** Reduces the `payment-records` DynamoDB table capacity to 1 RCU / 1 WCU, then runs a load generator against POST /orders with 10 concurrent requests for 20 seconds. The payment-validation-service starts getting throttled by DynamoDB, which cascades as errors in the order-processing-service.

**After injection:**
1. Click "Burst Test (10 concurrent)" on the dashboard
2. Watch most requests fail with 500 errors
3. Status badge flips to DEGRADED or SERVICE DOWN

**Talking points:**
- "We've just simulated a capacity reduction on an upstream service's database — maybe someone was trying to save costs, or a Terraform variable got misconfigured."
- "Notice: the order service code hasn't changed. The order service's own DynamoDB table is fine. But orders are failing because a dependency is broken."
- "The alert will fire on the order service — that's where the symptoms are visible. But the root cause is somewhere else entirely."

### Phase C2: Fire Webhook (1 minute)

**What to do:** Send the cascading failure alert to DevOps Agent.

```bash
python3 demo-app/scripts/simulate_webhook.py --scenario cascading-failure
```

**Talking point:** "The alert says 'Order Processing Service — elevated error rate and timeouts on POST /orders.' It doesn't mention the payment service at all. The agent has to figure out the cross-service dependency on its own."

### Phase C3: Agent Investigates (13 minutes)

**What to do:** Switch to the DevOps Agent console. Watch and narrate as the agent traces across service boundaries.

**Expected agent investigation path:**

1. **Check order-processing-service logs** → Finds `PaymentValidationError` and `PaymentValidationTimeout` entries
2. **Find payment validation errors** → Notices `upstream_function: "payment-validation-service"` in structured log fields
3. **Trace to payment-validation-service** → Uses service-mapping.json to discover the dependency and its resources
4. **Check payment-validation-service logs** → Finds `ProvisionedThroughputExceededException` errors
5. **Find DynamoDB throttling** → Correlates the throttling exceptions with the `payment-records` table
6. **Check DynamoDB table configuration** → Discovers capacity is set to 1 RCU / 1 WCU (abnormally low)
7. **Identify capacity reduction as root cause** → Checks CloudTrail, finds `UpdateTable` API call that reduced capacity

**Narration while agent works:**
- "It's checking the order service logs first — that's where the alert pointed..."
- "It found payment validation errors. Now it's looking at the `upstream_function` field in the logs..."
- "It's tracing to the payment-validation-service using the service mapping — this is the cross-service correlation step..."
- "Now it's in the payment service logs — it found DynamoDB throttling exceptions..."
- "It's checking the DynamoDB table config... capacity is 1/1. That's way too low for production traffic."
- "Root cause identified: someone reduced the payment-records table capacity, causing throttling that cascaded to the order service."

**Key talking point:** "Notice the investigation path: alert on Service A → logs reveal upstream dependency → trace to Service B → find the actual infrastructure issue. A human would need to open multiple consoles, correlate timestamps, and know which services depend on which. The agent did it by following the evidence trail in the logs and the service mapping."

### Phase C4: Reset & Recovery (4 minutes)

**What to do:** Reset the environment and show recovery.

```bash
bash demo-app/scripts/reset.sh
```

**Expected recovery behavior:**
- Payment-records table capacity restored to 5 RCU / 5 WCU
- `payment-records-throttle-alarm` returns to OK state within 2 minutes
- POST /orders requests start succeeding (verified by the reset script)
- Dashboard returns to healthy state (green status badge)

**After reset:**
1. Refresh the dashboard — status should return to green
2. Click "Burst Test (10 concurrent)" — all requests should succeed
3. Point out the recovery in the activity log

**Talking points:**
- "The fix is straightforward once you know the root cause — restore the DynamoDB capacity."
- "The hard part was finding the root cause across service boundaries. That's what took the agent 3-5 minutes instead of the 30-60 minutes it would take a human."
- "This pattern — alert on one service, root cause in another — is extremely common in microservice architectures. It's one of the hardest classes of incidents to debug manually."

---

## Backup Plan

If the live demo fails (agent doesn't start, webhook rejected, etc.):
1. Show the previous investigation result from the code bug scenario (already in the agent's history)
2. Walk through the agent's findings as a "here's what it found last time we ran this"
3. Pivot to Q&A earlier

---

## Commands Quick Reference

```bash
# Reset to healthy
bash demo-app/scripts/reset.sh

# Inject throttling (PRIMARY SCENARIO)
bash demo-app/scripts/inject-throttling.sh

# Inject cascading failure (ADVANCED SCENARIO)
bash demo-app/scripts/inject-cascading-failure.sh

# Inject code bug (BACKUP SCENARIO)
bash demo-app/scripts/inject-code-bug.sh

# Fire webhook
python3 demo-app/scripts/simulate_webhook.py --scenario throttling
python3 demo-app/scripts/simulate_webhook.py --scenario cascading-failure
python3 demo-app/scripts/simulate_webhook.py --scenario code-bug

# Open dashboard
open demo-app/dashboard/index.html

# Verify health
curl https://<your-api-id>.execute-api.us-east-1.amazonaws.com/health
```

---

## Cost Estimate

| Resource | Cost |
|----------|------|
| Lambda (order-processing-service) | ~$0.50/day during demo |
| DynamoDB (order-records) | ~$0.10/day (on-demand) |
| API Gateway | ~$0.01/day |
| CloudWatch Logs | ~$0.10/day |
| DevOps Agent | Free trial (2 months) |
| **Total idle cost** | **~$0.71/day** |
