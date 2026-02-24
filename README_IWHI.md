# IBM Hybrid Integration (IWHI) Management Guide

Repository: https://github.com/bingwang53/Bing_ProductOrder_APIs

This document explains how to manage the `Bing_ProductOrder_APIs` project in IBM Hybrid Integration using API Connect (APIC), API Gateway/DataPower runtime, and GitHub delivery practices.

## 1. Architecture Overview

- Backend implementation: FastAPI (`main.py`)
- Data store: MySQL (`product_order_db`)
- API contract: `openapi-apic-v2.json`
- API management plane: IBM API Connect (APIC)
- Runtime/data plane: API Gateway (DataPower)
- Source control: GitHub

Flow:

1. Client app (PHP/web/mobile) calls APIC endpoint
2. APIC Gateway enforces security and policies
3. APIC forwards to backend FastAPI service
4. FastAPI reads/writes MySQL
5. APIC Analytics tracks traffic, latency, and errors

## 2. Artifacts in This Repo

- `openapi-apic-v2.json` (recommended for APIC import)
- `openapi-apic.json` / `openapi.json` (other generated variants)
- `README.md` (local dev and demo instructions)
- API source: `main.py`

## 3. APIC Setup (Provider Side)

1. Open APIC API Manager
2. Select your Provider Organization
3. Go to `Develop -> APIs`
4. Import `openapi-apic-v2.json`
5. Open `Assemble` and configure `Invoke` target URL
6. Add security policies (API key/OAuth/JWT)
7. Add traffic policies (rate limit/quota)
8. Save API
9. Create Product and Plan
10. Publish Product to a Catalog

## 4. Runtime Connectivity Requirements

APIC Gateway must be able to reach your backend target.

- APIC SaaS cannot call `localhost`/`127.0.0.1`
- Use a reachable HTTPS endpoint (approved runtime, DMZ, or approved secure connectivity)
- Validate endpoint health before publishing

## 5. Security Baseline

Recommended minimum controls:

- Require API key (or OAuth)
- Enforce TLS in all environments
- Add rate limiting and quota per plan
- Restrict CORS origins if browser clients are used
- Disable anonymous access in production

## 6. Product and Plan Strategy

Suggested structure:

- Product: `Bing ProductOrder APIs`
- Plan examples:
  - `trial` (low limits)
  - `standard` (moderate limits)
  - `premium` (higher limits + SLA)

This lets you control consumer onboarding and usage by subscription.

## 7. Analytics and Operations

Use APIC Analytics to monitor:

- Request count by API/product/app
- 4xx/5xx trends
- Latency percentiles
- Top consuming applications

Operational checks:

1. Verify success rate after deployments
2. Watch for throttling spikes (`429`)
3. Track backend timeouts/errors

## 8. Change and Release Process (GitHub -> APIC)

Recommended workflow:

1. Update API/backend in feature branch
2. Regenerate OpenAPI contract (`openapi-apic-v2.json`)
3. Open pull request and review
4. Merge to `main`
5. Deploy/import updated API to APIC
6. Stage and publish updated Product version
7. Validate in test catalog before production catalog

## 9. Versioning Guidance

- Use semantic versions in API info and Product versions
- Keep old major versions active during migration
- Communicate deprecation windows to consumers

## 10. Demo Story (Business Value)

- Online order arrives from front-end app
- APIC enforces policy and governance
- Backend writes order to MySQL
- Team updates order status through managed APIs
- APIC analytics provides runtime visibility

Business outcome:

- Controlled exposure
- Standardized security
- Better observability
- Faster onboarding of internal/external consumers

## 11. Troubleshooting

- Import validation error:
  - Use `openapi-apic-v2.json`
- Calls fail at gateway:
  - Check `Invoke` target reachability from APIC runtime
- Unauthorized errors:
  - Confirm app subscription and credentials
- No analytics data:
  - Confirm calls go through APIC endpoint (not direct backend)

## 12. Quick Checklist

Before go-live:

- API imported and validated in APIC
- Security policies enabled
- Product/Plan published
- Consumer app subscribed
- Backend reachability confirmed
- Analytics dashboard verified

