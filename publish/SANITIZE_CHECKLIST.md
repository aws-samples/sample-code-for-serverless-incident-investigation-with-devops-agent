# Pre-Publish Sanitization Checklist

Before pushing to aws-samples, ensure these items are addressed:

## Secrets to Remove

- [x] `scripts/simulate_webhook.py` — lines 14-15 contain hardcoded `WEBHOOK_URL` and `WEBHOOK_SECRET`
  - **Fixed**: Replaced with `os.environ.get("WEBHOOK_URL")` and `os.environ.get("WEBHOOK_SECRET")` with validation

- [x] `infra/lambda-template.yaml` — `AlarmForwarderFunction` environment variables contain real webhook URL/secret
  - **Fixed**: Uses `!Ref` parameters (`WebhookUrl` and `WebhookSecret`) with `NoEcho: true`

## Account-Specific References to Remove

- [x] API Gateway ID `rut1bpvz79` in docs/presenter-guide.md, scripts, and dashboard
  - **Fixed**: Replaced with `<your-api-id>` placeholder; scripts use `${API_URL:-...}` env var pattern
- [x] Account ID `018237412703` in scripts and docs
  - **Fixed**: Replaced with example account `123456789012` in webhook scenarios; removed from presenter-guide
- [x] Webhook endpoint `7a7dadeb-9d9e-444d-ba70-b08882e2c485`
  - **Fixed**: Removed from source files (now read from environment variables)

## Files to Exclude from Publication

- [ ] `.aws-sam/` directory (build artifacts) — add to `.gitignore` or exclude from publish
- [ ] `__pycache__/` directories — already in `.gitignore`
- [ ] `docs/demo-transcript.md` (internal presentation notes)
- [ ] `docs/guardrail-harness-presentation.md` (unrelated project)
- [ ] `Dockerfile` / `Dockerfile.buggy` (ECS variant, not used in Lambda demo)
- [ ] `infra/template.yaml` (ECS variant, not used)

## AWS Samples Requirements

- [x] MIT-0 License file
- [x] CONTRIBUTING.md
- [x] README.md with architecture, prerequisites, and quick start
- [x] Copyright headers in source files
- [x] No internal Amazon references (wiki links, internal tools, etc.)
- [ ] Repository name follows convention: `aws-devops-agent-incident-demo` or similar
- [x] `NOTICE` file present

