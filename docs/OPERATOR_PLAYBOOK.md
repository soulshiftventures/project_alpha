# Project Alpha - Operator Playbook

A practical guide for operators to use Project Alpha effectively and safely.

## Quick Reference

| Task | Route | Description |
|------|-------|-------------|
| Check system status | `/` | Dashboard with attention items |
| View work queue | `/work-queue` | All items needing attention |
| Review approvals | `/approvals` | Approve or deny pending actions |
| Run scenarios | `/scenarios` | Execute workflow templates |
| Check connector health | `/integrations` | Verify external service connections |
| Resume blocked work | `/recovery` | Handle paused/failed workflows |

---

## 1. Getting Started

### First-Time Setup

1. **Verify readiness**: Visit `/readiness` to confirm all components are operational
2. **Review setup checklist**: Visit `/setup` for the complete first-use guide
3. **Configure credentials**: Set environment variables for connectors you plan to use
4. **Run health check**: Visit `/health` to confirm all subsystems are healthy

### Starting the System

```bash
# Full startup with readiness check
./run_full.sh

# Or start directly
PYTHONPATH=. python3 ui/app.py
```

Then visit http://localhost:5000

---

## 2. Daily Operator Workflow

### Morning Checklist

1. **Check the dashboard** (`/`) - Review attention banner and status cards
2. **Process work queue** (`/work-queue`) - Handle pending items by priority
3. **Review pending approvals** (`/approvals`) - Approve or deny queued actions
4. **Check connector health** (`/integrations`) - Verify external services are reachable
5. **Review costs** (`/costs`) - Monitor budget utilization

### Working Through the Queue

The work queue (`/work-queue`) combines all items needing attention:

| Queue Type | Priority | Actions |
|------------|----------|---------|
| Pending Approvals | Normal-High | Approve, Deny |
| Paused Scenarios | Medium | Resume, Retry, Skip, Cancel |
| Failed Jobs | High | Retry, Rerun Plan |
| Active Blockers | High | Resolve, Skip |

**Recommended approach:**
1. Process high-priority items first (failed jobs, blockers)
2. Handle pending approvals next
3. Resume any paused scenarios last

---

## 3. Common Workflows

### A. Submit a New Discovery

1. Go to `/discovery`
2. Enter your idea, problem, or opportunity in the intake form
3. Add optional tags for categorization
4. Submit and review the generated opportunity record
5. Choose a handoff mode: **Pursue Now**, **Validate First**, or **Archive**

### B. Run a Scenario

1. Go to `/scenarios`
2. Browse available scenarios by category
3. Click a scenario to view its details and required inputs
4. Fill in the input fields
5. Choose **Dry Run** (safe) or **Live** mode
6. Click "Run Scenario"
7. Monitor execution at `/scenarios/runs/<run_id>`

### C. Approve a Pending Action

1. Go to `/approvals` or `/work-queue`
2. Review the action description and risk level
3. Click the approval record to see full details
4. Enter rationale (optional)
5. Click **Approve** or **Deny**
6. If approving a live-mode action, decide whether to promote to live

### D. Resume a Blocked Workflow

1. Go to `/work-queue` and filter by "paused"
2. Or go to `/recovery` for the full recovery dashboard
3. Review what's blocking the workflow
4. Take appropriate action:
   - **Approve blocker**: If waiting on approval, go approve it
   - **Add credential**: If missing credential, configure it in environment
   - **Skip step**: If step is non-critical, skip and continue
   - **Retry step**: If transient error, retry the failed step
   - **Cancel**: If workflow should not continue

### E. Check Connector Health

1. Go to `/integrations`
2. View connector status cards
3. Click a connector for detailed status
4. Click "Health Check" to run a live connectivity test
5. Review credential requirements if connector shows "Not Ready"

---

## 4. Dry-Run vs Live Mode

Project Alpha uses a two-mode execution model for safety:

### Dry-Run Mode (Default)
- All actions are simulated
- No external API calls are made
- Safe for testing and validation
- Results show what *would* happen

### Live Mode
- Real API calls to external services
- Requires explicit promotion
- Requires valid credentials
- Gated by policy and approval workflow

### How to Enable Live Mode

1. Configure required credentials in environment
2. Request approval for the operation (automatic or manual)
3. Approve the request at `/approvals`
4. Check "Promote to Live Mode" when approving
5. Future runs of that operation will execute live

### Checking Live-Ready Status

- Visit `/readiness` to see which connectors are live-capable
- A connector is live-ready when:
  - Credentials are configured
  - Policy allows live execution
  - Standing approval exists (or per-request approval granted)

---

## 5. Recovery Procedures

### Paused Scenario

**Symptoms:** Scenario shows "awaiting_approval" or "partial" status

**Resolution:**
1. Go to `/work-queue` and find the paused scenario
2. Check the "blockers" to understand why it's paused
3. If blocked on approval: approve the pending request
4. If blocked on credential: add the missing credential
5. Click "Resume" to continue execution

### Failed Job

**Symptoms:** Job shows "failed" status with error message

**Resolution:**
1. Go to `/work-queue` and find the failed job
2. Review the error message
3. If transient error: click "Retry"
4. If configuration error: fix config and click "Rerun Plan"
5. If persistent error: investigate logs at `/events`

### Missing Credential

**Symptoms:** Connector shows "Not Ready" or action fails with credential error

**Resolution:**
1. Identify required credential from `/setup` or connector detail page
2. Set the environment variable:
   ```bash
   export CONNECTOR_API_KEY="your-key-here"
   ```
3. Restart the application
4. Verify at `/credentials`

### Budget Exceeded

**Symptoms:** Actions blocked with budget warning

**Resolution:**
1. Check budget status at `/costs`
2. Review spending by connector and business
3. Either increase budget limit or wait for period reset
4. For urgent actions, request budget override approval

---

## 6. Safety Guidelines

### Always Do
- Start with dry-run mode for new scenarios
- Review approval requests before approving
- Check connector health before running live actions
- Monitor the work queue regularly
- Review costs periodically

### Never Do
- Approve actions without reviewing details
- Commit credentials to source control
- Run live mode without valid credentials configured
- Ignore failed jobs or blockers for extended periods
- Bypass the approval workflow

### Emergency Procedures

**If a live action is causing problems:**
1. Go to `/work-queue`
2. Find the running scenario or job
3. Click "Cancel" immediately
4. Review logs at `/events`
5. Investigate at `/connector-actions` for recent executions

---

## 7. Connector Reference

### Currently Supported Connectors

| Connector | Live Actions | Required Credentials |
|-----------|--------------|---------------------|
| Telegram | send_message, get_updates | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` |
| Tavily | search, extract | `TAVILY_API_KEY` |
| SendGrid | send_email | `SENDGRID_API_KEY`, `SENDGRID_FROM_EMAIL` |
| HubSpot | create_contact, update_contact | `HUBSPOT_API_KEY` |
| Firecrawl | scrape | `FIRECRAWL_API_KEY` |
| Apollo | (placeholder) | Not yet implemented |

### Connector Health States

| State | Meaning | Action |
|-------|---------|--------|
| Ready | Credentials configured, passes health check | Can run live |
| Degraded | Credentials exist but health check failing | Check connectivity |
| Not Ready | Missing credentials | Configure credentials |
| Error | Unexpected failure | Check logs |

---

## 8. Template Quick Reference

### Available First-Run Templates

| Template | Purpose | Mode |
|----------|---------|------|
| discovery_intake | Submit new business idea | Dry-run |
| validation_first | Research before committing | Dry-run |
| research_scenario | Run market/competitor research | Dry-run |
| notification_test | Test notification delivery | Dry-run or Live |
| crm_update | Update CRM contact | Dry-run or Live |
| connector_health | Check all connector status | Read-only |

### Using Templates

1. Go to `/templates`
2. Browse templates by category
3. Click a template to see its inputs and steps
4. Click "Launch" to start a guided workflow
5. Fill in required inputs
6. Review the execution plan
7. Confirm execution

---

## 9. Troubleshooting

### "No scenarios available"
- Verify the scenario registry is initialized
- Check `/api/scenarios` for raw data
- Review logs for initialization errors

### "Approval not found"
- Approval may have already been processed
- Check `/approvals` history tab
- May need to resubmit the request

### "Connector not ready"
- Check environment variables
- Restart application after setting credentials
- Verify credential format matches expected pattern

### "Budget exceeded"
- Review `/costs` for spending breakdown
- Check if budget was recently reset
- May need admin to increase budget limit

### "Scenario stuck in partial state"
- Check for active blockers at `/recovery/blockers`
- May need to manually skip or cancel
- Check if required approval is pending

---

## 10. API Quick Reference

### Status Endpoints
```
GET /api/status                - System status
GET /api/combined-status       - Health + readiness combined
GET /api/attention-summary     - Items needing attention
GET /api/quick-counts          - Action counts for dashboard
```

### Work Queue
```
GET /api/work-queue            - Unified work queue
GET /api/work-queue?type=X     - Filter by type (approval, scenario, job, blocker)
```

### Recovery
```
POST /api/recovery/resume/scenario/<id>  - Resume paused scenario
POST /api/recovery/retry/job/<id>        - Retry failed job
POST /api/recovery/skip/step/<id>/<step> - Skip blocked step
POST /api/recovery/cancel/scenario/<id>  - Cancel scenario
```

### Templates
```
GET /api/templates             - List templates
GET /api/templates/<id>        - Get template details
POST /api/templates/<id>/launch - Launch template workflow
```

---

## Support

For issues or questions:
1. Check the event log at `/events` for detailed error messages
2. Review this playbook for common procedures
3. Check `/readiness` and `/health` for system status
4. Consult the README.md for technical documentation
