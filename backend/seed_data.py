"""
Seed Script — Populates the database with 20 diverse test scenarios.
Each scenario has a full agent reasoning chain for frontend display.

Run: python seed_data.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from src.db import run_migration, execute, fetch_one
from datetime import datetime, timedelta
import random

run_migration()

# ── Clear existing data ──────────────────────────────────────────
execute("DELETE FROM SP_AGENT_EVENTS")
execute("DELETE FROM SP_INCIDENTS")
print("Cleared existing data.")


# ── 20 Diverse Scenarios ─────────────────────────────────────────

SCENARIOS = [
    # ── P1 Critical (5) ──────────────────────────────────────────
    {
        "id": "INC-A9F21B01", "source": "email", "severity": "P1", "status": "Resolved", "issue_type": "CODE",
        "desc": "[SP-301] NullPointerException in PaymentService.java causing checkout failures for all users",
        "rca": "PaymentService.java:145 — user.getBalance() returns null when wallet is empty. Missing null check introduced in PR #4012.",
        "resolution": "Drafted PR #1043 to add null check: if (user.getBalance() == null) return BigDecimal.ZERO",
        "confidence": 0.92, "approval": True, "approved": True, "jira_key": "SP-301",
        "events": [
            ("Triage Agent", "Classified as P1 — Critical. Keyword match: 'NullPointerException', 'checkout failures'. Found 3 similar historical tickets.", "Local File"),
            ("Telemetry Agent", "Parsed 847 log entries. Found 523 ERROR entries in last 15min. Anomaly: error rate spike from 0.1% → 22%. Suspected: PaymentService, PaymentGateway.", "Splunk MCP"),
            ("Codebase Agent", "Identified CODE issue. Root cause: Missing null guard in PaymentService.java line 145. PR #4012 removed defensive check.", "GitHub MCP"),
            ("Resolution Agent", "Drafted PR #1043 with null check fix. Confidence: 92%. Requires L3 Engineering approval. Jira ticket SP-301 created.", "Jira + Outlook MCP"),
        ]
    },
    {
        "id": "INC-C4D89202", "source": "monitoring", "severity": "P1", "status": "Resolved", "issue_type": "INFRA",
        "desc": "Database connection pool exhaustion — HikariPool-1 reporting 100% utilization and timeout errors",
        "rca": "HikariPool max connections set to 50, traffic spike caused 100% pool utilization. Auto-scale Terraform rule had 30-min threshold, pool exhausted in 15 min.",
        "resolution": "Increased max database connection pool size from 50 to 100 via Terraform apply. Auto-scale threshold reduced to 10 min.",
        "confidence": 0.99, "approval": False, "approved": None, "jira_key": "SP-302",
        "events": [
            ("Triage Agent", "Classified as P1 — Critical. Infrastructure alert. Connection pool exhaustion detected. Found 2 similar historical tickets.", "Local File"),
            ("Telemetry Agent", "Parsed 1,204 log entries. Found 89 WARN and 156 ERROR entries. Anomaly: HikariPool active=100/100, idle=0, waiting=45.", "Splunk MCP"),
            ("Codebase Agent", "Identified INFRA issue. Terraform config shows max_pool_size=50. Auto-scale rule threshold=95% for 30min.", "GitHub MCP"),
            ("Resolution Agent", "Applied Terraform change: max_pool_size=100, auto-scale threshold=10min. Auto-remediated (no approval needed). Confidence: 99%.", "Jira + Outlook MCP"),
        ]
    },
    {
        "id": "INC-E7B34503", "source": "slack", "severity": "P1", "status": "Pending Human Approval", "issue_type": "DATA",
        "desc": "[SP-303] 2,400 customer orders stuck in PENDING state for 6+ hours — payment was charged but orders not fulfilled",
        "rca": "Batch job `order_fulfillment_cron` failed silently at 02:00 UTC. Dead letter queue accumulated 2,400 messages. DB shows payment_status=COMPLETED but order_status=PENDING.",
        "resolution": "Execute recovery SQL: UPDATE orders SET order_status='PROCESSING' WHERE payment_status='COMPLETED' AND order_status='PENDING' AND created_at > '2024-05-20'",
        "confidence": 0.85, "approval": True, "approved": False, "jira_key": "SP-303",
        "events": [
            ("Triage Agent", "Classified as P1 — Critical. Data integrity issue. 2,400 orders affected. Revenue impact: ~$180K. Found 1 similar ticket from April.", "Email MCP"),
            ("Telemetry Agent", "Found 2,400 dead letter queue messages. Cron job exit code 137 (OOM killed). Memory spike at 01:58 UTC.", "Splunk MCP"),
            ("Codebase Agent", "Identified DATA issue. order_fulfillment_cron has no retry logic. Memory limit set to 512MB, job processes all pending orders in one batch.", "GitHub MCP"),
            ("Resolution Agent", "Recovery SQL prepared for 2,400 orders. Requires L2 approval for data mutation. Jira SP-303 created. Stakeholders notified.", "Jira + Outlook MCP"),
        ]
    },
    {
        "id": "INC-F1A56704", "source": "pagerduty", "severity": "P1", "status": "Resolved", "issue_type": "INFRA",
        "desc": "API Gateway returning 503 Service Unavailable for all endpoints — complete service outage",
        "rca": "SSL certificate expired at 00:00 UTC. Auto-renewal Certbot cron was disabled during last maintenance window and never re-enabled.",
        "resolution": "Renewed SSL certificate via Certbot. Re-enabled auto-renewal cron. Added certificate expiry monitoring alert (7-day warning).",
        "confidence": 0.98, "approval": False, "approved": None, "jira_key": None,
        "events": [
            ("Triage Agent", "Classified as P1 — Critical. Complete service outage. All endpoints returning 503. Uptime monitoring triggered.", "Email MCP"),
            ("Telemetry Agent", "100% error rate across all services. TLS handshake failures in nginx logs. Certificate expiry: 2024-05-20T00:00:00Z.", "Splunk MCP"),
            ("Codebase Agent", "Identified INFRA issue. Certbot cron disabled (commented out in /etc/crontab). Last renewal: 60 days ago.", "GitHub MCP"),
            ("Resolution Agent", "Certificate renewed. Cron re-enabled. Monitoring alert added. Auto-remediated. Confidence: 98%.", "Jira + Outlook MCP"),
        ]
    },
    {
        "id": "INC-92D78005", "source": "email", "severity": "P1", "status": "Failed", "issue_type": "UNKNOWN",
        "desc": "[SP-305] Intermittent 504 Gateway Timeout errors on /api/search endpoint — affecting 15% of search queries",
        "rca": "Unable to determine definitive root cause. Possible causes: Elasticsearch cluster rebalancing, network latency spikes, JVM garbage collection pauses.",
        "resolution": "Unable to determine root cause. Escalating to human L1. Recommended: review ES cluster health, JVM heap settings, and network traces.",
        "confidence": 0.10, "approval": True, "approved": False, "jira_key": "SP-305",
        "events": [
            ("Triage Agent", "Classified as P1 — Critical. Intermittent failures, 15% of queries affected. No clear pattern. Found 0 similar tickets.", "Local File"),
            ("Telemetry Agent", "Sporadic 504 errors across 3 API pods. No consistent correlation with CPU/memory. ES cluster shows intermittent rebalancing.", "Splunk MCP"),
            ("Codebase Agent", "Could not identify specific code or infra issue. Search service code unchanged in 2 weeks. Issue may be external.", "GitHub MCP"),
            ("Resolution Agent", "Confidence too low (10%) for automated fix. Escalating to human L1. Multiple possible root causes identified.", "System"),
        ]
    },

    # ── P2 High (8) ──────────────────────────────────────────────
    {
        "id": "INC-3AB12106", "source": "monitoring", "severity": "P2", "status": "Resolved", "issue_type": "CODE",
        "desc": "[SP-306] Memory leak in UserSessionService causing gradual heap exhaustion — OOM kills every 8 hours",
        "rca": "HashMap in UserSessionService.java stores session objects but never removes expired ones. Heap grows linearly until OOM at ~4GB.",
        "resolution": "Drafted PR #1044 to add TTL-based eviction using ConcurrentHashMap with scheduled cleanup. Added -XX:+HeapDumpOnOutOfMemoryError JVM flag.",
        "confidence": 0.88, "approval": True, "approved": True, "jira_key": "SP-306",
        "events": [
            ("Triage Agent", "Classified as P2. Memory leak pattern detected. Service restarts every 8 hours. Found 1 similar historical ticket.", "Local File"),
            ("Telemetry Agent", "Heap usage pattern: linear growth from 500MB to 4GB over 8h. GC frequency increasing. 3 OOM kills in last 24h.", "Splunk MCP"),
            ("Codebase Agent", "Identified CODE issue. UserSessionService.java line 89: sessions HashMap grows unbounded. No TTL or eviction policy.", "GitHub MCP"),
            ("Resolution Agent", "PR #1044 adds TTL eviction. JVM heap dump flag added. Confidence: 88%. Requires L3 approval.", "Jira + Outlook MCP"),
        ]
    },
    {
        "id": "INC-5BC23207", "source": "jira", "severity": "P2", "status": "Resolved", "issue_type": "INFRA",
        "desc": "Redis cache hit ratio dropped from 95% to 40% — causing 3x increase in database load",
        "rca": "Redis maxmemory-policy changed from 'allkeys-lru' to 'noeviction' during config migration. Cache fills up and stops accepting new keys.",
        "resolution": "Restored Redis maxmemory-policy to 'allkeys-lru'. Flushed stale keys. Added config drift detection alert.",
        "confidence": 0.96, "approval": False, "approved": None, "jira_key": None,
        "events": [
            ("Triage Agent", "Classified as P2. Performance degradation. Cache miss rate spiked. DB load 3x normal.", "Email MCP"),
            ("Telemetry Agent", "Redis INFO shows maxmemory-policy: noeviction. Used memory: 100% of maxmemory. Rejected commands: 12,450.", "Splunk MCP"),
            ("Codebase Agent", "Identified INFRA issue. Redis config changed in last deployment. Config diff shows policy change.", "GitHub MCP"),
            ("Resolution Agent", "Config restored to allkeys-lru. Cache flushed. Auto-remediated. Confidence: 96%.", "Jira + Outlook MCP"),
        ]
    },
    {
        "id": "INC-6CD34308", "source": "email", "severity": "P2", "status": "Resolved", "issue_type": "CODE",
        "desc": "[SP-308] Authentication tokens not refreshing — users logged out after 15 minutes despite Remember Me setting",
        "rca": "JWT refresh token endpoint returns 200 but sends expired token. Bug in TokenService.java: refresh uses original expiry instead of generating new one.",
        "resolution": "PR #1045 fixes TokenService.refreshToken() to generate new expiry timestamp. Added unit test for refresh flow.",
        "confidence": 0.91, "approval": True, "approved": True, "jira_key": "SP-308",
        "events": [
            ("Triage Agent", "Classified as P2. Auth issue affecting all users with 'Remember Me'. 4,200 support tickets in last 2 hours.", "Local File"),
            ("Telemetry Agent", "Token refresh endpoint returns 200 but auth failures spike 15min later. Pattern matches token expiry window.", "Splunk MCP"),
            ("Codebase Agent", "Identified CODE issue. TokenService.java line 67: refreshToken() copies original exp claim instead of generating new one.", "GitHub MCP"),
            ("Resolution Agent", "PR #1045 fixes refresh logic. Unit test added. Confidence: 91%. Requires L3 approval.", "Jira + Outlook MCP"),
        ]
    },
    {
        "id": "INC-7DE45409", "source": "slack", "severity": "P2", "status": "Pending Human Approval", "issue_type": "DATA",
        "desc": "[SP-309] Price sync job imported 0.00 prices for 340 products from ERP — customers ordering items for free",
        "rca": "ERP export contained null prices for 340 SKUs due to upstream data entry error. Price sync job treats null as 0 instead of skipping.",
        "resolution": "SQL rollback: UPDATE products SET price = previous_price WHERE price = 0 AND updated_at > '2024-05-20T06:00:00'. Add null price validation to sync job.",
        "confidence": 0.87, "approval": True, "approved": False, "jira_key": "SP-309",
        "events": [
            ("Triage Agent", "Classified as P2. Revenue impacting — 340 products at €0. 47 orders placed at zero price. €12K revenue loss.", "Email MCP"),
            ("Telemetry Agent", "Price sync job completed at 06:15 UTC. 340 UPDATE statements with price=0. No validation errors logged.", "Splunk MCP"),
            ("Codebase Agent", "Identified DATA issue. PriceSyncJob.java line 112: null prices coerced to BigDecimal.ZERO instead of being skipped.", "GitHub MCP"),
            ("Resolution Agent", "Rollback SQL prepared for 340 products. 47 orders need manual review. Requires L2 approval. Jira SP-309 created.", "Jira + Outlook MCP"),
        ]
    },
    {
        "id": "INC-8EF56510", "source": "monitoring", "severity": "P2", "status": "Resolved", "issue_type": "INFRA",
        "desc": "Kubernetes pod crash loop — order-processing deployment restarting every 2 minutes",
        "rca": "Liveness probe timeout set to 5s, but service startup takes 12s after adding new health check dependency. Pod killed before fully starting.",
        "resolution": "Increased liveness probe initialDelaySeconds from 10 to 30. Increased timeout from 5s to 15s. Added startupProbe.",
        "confidence": 0.97, "approval": False, "approved": None, "jira_key": "SP-310",
        "events": [
            ("Triage Agent", "Classified as P2. CrashLoopBackOff on order-processing. 45 restarts in last 90 minutes.", "Email MCP"),
            ("Telemetry Agent", "Pod lifecycle events show: Started → LivenessProbe failed → Killed → Restarting. Consistent 2-min cycle.", "Splunk MCP"),
            ("Codebase Agent", "Identified INFRA issue. Liveness probe config: initialDelay=10s, timeout=5s. Service startup logs show ready at 12s.", "GitHub MCP"),
            ("Resolution Agent", "Updated probe config. Added startupProbe. Auto-remediated. Confidence: 97%.", "Jira + Outlook MCP"),
        ]
    },
    {
        "id": "INC-9FA67611", "source": "email", "severity": "P2", "status": "Resolved", "issue_type": "CODE",
        "desc": "Email notification service sending duplicate emails — customers receiving 3-5 copies of each order confirmation",
        "rca": "Message queue consumer lacks idempotency check. Network timeout causes message redelivery, consumer processes same message multiple times.",
        "resolution": "PR #1046 adds idempotency key (messageId) to consumer with 24h dedup window using Redis SET NX. Added dead letter queue for poison messages.",
        "confidence": 0.90, "approval": True, "approved": True, "jira_key": "SP-311",
        "events": [
            ("Triage Agent", "Classified as P2. 8,300 duplicate emails sent in last 4 hours. Customer complaints spiking. Brand reputation risk.", "Local File"),
            ("Telemetry Agent", "RabbitMQ shows high redelivery count. Consumer ack timeout causing requeue. 3-5x message duplication per order.", "Splunk MCP"),
            ("Codebase Agent", "Identified CODE issue. EmailConsumer.java: no idempotency check. processMessage() has no dedup logic.", "GitHub MCP"),
            ("Resolution Agent", "PR #1046 adds Redis-based idempotency. DLQ configured. Confidence: 90%. Requires L3 approval.", "Jira + Outlook MCP"),
        ]
    },
    {
        "id": "INC-AFB78712", "source": "pagerduty", "severity": "P2", "status": "Resolved", "issue_type": "INFRA",
        "desc": "CDN cache purge failed — users seeing stale product images and prices after catalog update",
        "rca": "CloudFront invalidation API call returned 429 (rate limited). Retry logic used fixed delay instead of backoff. Purge abandoned after 3 attempts.",
        "resolution": "Fixed CDN purge to use exponential backoff. Added wildcard invalidation for batch updates. Manually purged stale paths.",
        "confidence": 0.94, "approval": False, "approved": None, "jira_key": None,
        "events": [
            ("Triage Agent", "Classified as P2. Stale content served to users. 12,000 product pages affected. Cache TTL: 24h.", "Email MCP"),
            ("Telemetry Agent", "CloudFront invalidation logs show 429 responses. 3 failed attempts. Stale cache age: 18 hours.", "Splunk MCP"),
            ("Codebase Agent", "Identified INFRA issue. CDNPurgeService.java: fixed 1s retry delay, no backoff. Max retries: 3.", "GitHub MCP"),
            ("Resolution Agent", "Backoff logic added. Manual purge executed. Auto-remediated. Confidence: 94%.", "Jira + Outlook MCP"),
        ]
    },
    {
        "id": "INC-B0C89813", "source": "monitoring", "severity": "P2", "status": "Processing", "issue_type": None,
        "desc": "Gradual increase in API response times — p99 latency doubled from 200ms to 400ms over last 3 days",
        "rca": "", "resolution": "", "confidence": 0.0, "approval": False, "approved": None, "jira_key": None,
        "events": [
            ("Triage Agent", "Classified as P2. Performance degradation trend. p99 latency increasing 30% daily. No immediate outage.", "Local File"),
            ("Telemetry Agent", "Analyzing latency distribution across services. Database query times increasing. Index fragmentation suspected.", "Splunk MCP"),
        ]
    },

    # ── P3 Low (7) ───────────────────────────────────────────────
    {
        "id": "INC-C1D90914", "source": "jira", "severity": "P3", "status": "Resolved", "issue_type": "CODE",
        "desc": "Dashboard chart tooltip showing wrong timezone — UTC instead of user's local time",
        "rca": "Frontend Chart.js config uses UTC by default. timezone option not set in chart configuration.",
        "resolution": "PR #1047 adds Intl.DateTimeFormat().resolvedOptions().timeZone to chart config. All tooltips now show local time.",
        "confidence": 0.95, "approval": True, "approved": True, "jira_key": "SP-314",
        "events": [
            ("Triage Agent", "Classified as P3. UI bug. Cosmetic issue. No business impact. 12 user reports.", "Local File"),
            ("Telemetry Agent", "No errors in logs. Frontend-only issue. No backend involvement.", "Splunk MCP"),
            ("Codebase Agent", "Identified CODE issue. DashboardChart.jsx line 34: Chart.defaults.timezone not configured.", "GitHub MCP"),
            ("Resolution Agent", "PR #1047 adds timezone config. Confidence: 95%. Requires L3 approval.", "Jira + Outlook MCP"),
        ]
    },
    {
        "id": "INC-D2EA1015", "source": "email", "severity": "P3", "status": "Resolved", "issue_type": "CODE",
        "desc": "Export CSV button generates file with incorrect date format — DD/MM/YYYY instead of YYYY-MM-DD (ISO 8601)",
        "rca": "ExportService uses SimpleDateFormat('dd/MM/yyyy') instead of ISO 8601 format, causing import failures in downstream systems.",
        "resolution": "PR #1048 changes date format to ISO 8601 (yyyy-MM-dd). Added format parameter to allow user-selected format in future.",
        "confidence": 0.93, "approval": True, "approved": True, "jira_key": None,
        "events": [
            ("Triage Agent", "Classified as P3. Data format issue. Downstream ETL job failing on date parse. Low urgency.", "Email MCP"),
            ("Telemetry Agent", "ETL job failure logs show DateParseException for exported CSV files. 3 failures in last week.", "Splunk MCP"),
            ("Codebase Agent", "Identified CODE issue. ExportService.java line 78: SimpleDateFormat uses 'dd/MM/yyyy' instead of 'yyyy-MM-dd'.", "GitHub MCP"),
            ("Resolution Agent", "PR #1048 fixes date format. Added configurable format parameter. Confidence: 93%.", "Jira + Outlook MCP"),
        ]
    },
    {
        "id": "INC-E3FB2116", "source": "slack", "severity": "P3", "status": "Resolved", "issue_type": "INFRA",
        "desc": "Log rotation not working — /var/log/app filling up disk at 2GB/day, 85% disk usage warning",
        "rca": "Logrotate config had wrong path (/var/log/application/*.log instead of /var/log/app/*.log). Logs never rotated since last deployment.",
        "resolution": "Fixed logrotate config path. Compressed and archived old logs. Freed 18GB disk space. Added disk usage alert at 70%.",
        "confidence": 0.97, "approval": False, "approved": None, "jira_key": None,
        "events": [
            ("Triage Agent", "Classified as P3. Disk space issue. Not customer-facing but risk of outage if disk fills.", "Local File"),
            ("Telemetry Agent", "Disk usage: 85%. Log files: 18GB unrotated. Growth rate: 2GB/day. ETA to 100%: 4 days.", "Splunk MCP"),
            ("Codebase Agent", "Identified INFRA issue. Logrotate config path mismatch: expected /var/log/app, configured /var/log/application.", "GitHub MCP"),
            ("Resolution Agent", "Config fixed. Old logs archived. Disk alert added. Auto-remediated. Confidence: 97%.", "Jira + Outlook MCP"),
        ]
    },
    {
        "id": "INC-F4GC3217", "source": "monitoring", "severity": "P3", "status": "Pending Human Approval", "issue_type": "CODE",
        "desc": "Swagger/OpenAPI docs not loading — /api/docs returns 500 error after adding new endpoint",
        "rca": "New endpoint uses Python 3.12 type hint syntax (int | None) in Pydantic model. FastAPI 0.95 doesn't fully support union syntax.",
        "resolution": "PR #1049 changes type hints to Optional[int] for backward compatibility. Alternatively, upgrade FastAPI to 0.100+.",
        "confidence": 0.89, "approval": True, "approved": False, "jira_key": "SP-317",
        "events": [
            ("Triage Agent", "Classified as P3. Developer tooling issue. API docs broken. No customer impact.", "Email MCP"),
            ("Telemetry Agent", "FastAPI /docs endpoint returns 500. Traceback shows PydanticUserError on type annotation.", "Splunk MCP"),
            ("Codebase Agent", "Identified CODE issue. NewEndpoint.py uses `int | None` syntax. FastAPI version: 0.95.2 (needs 0.100+).", "GitHub MCP"),
            ("Resolution Agent", "PR #1049 uses Optional[int] syntax. Alternative: upgrade FastAPI. Confidence: 89%. Requires L3 approval.", "Jira + Outlook MCP"),
        ]
    },
    {
        "id": "INC-G5HD4318", "source": "email", "severity": "P3", "status": "Resolved", "issue_type": "DATA",
        "desc": "Analytics dashboard showing negative revenue numbers for 3 product categories",
        "rca": "ETL job double-counted refunds. Refund events processed twice due to event replay after Kafka consumer group rebalance.",
        "resolution": "Fixed Kafka consumer offset management. Recalculated revenue for affected categories. Data corrected in reporting DB.",
        "confidence": 0.86, "approval": True, "approved": True, "jira_key": "SP-318",
        "events": [
            ("Triage Agent", "Classified as P3. Reporting data error. No customer impact. Internal dashboard shows incorrect numbers.", "Local File"),
            ("Telemetry Agent", "Kafka consumer group rebalanced 3 times yesterday. Refund events processed 2x each. Offset management issue.", "Splunk MCP"),
            ("Codebase Agent", "Identified DATA issue. RevenueETL.java: no idempotent processing. Consumer offset committed after batch, not per-message.", "GitHub MCP"),
            ("Resolution Agent", "Offset management fixed. Revenue recalculated. Data corrected. Confidence: 86%. Requires L2 approval.", "Jira + Outlook MCP"),
        ]
    },
    {
        "id": "INC-H6IE5419", "source": "jira", "severity": "P3", "status": "Resolved", "issue_type": "INFRA",
        "desc": "Staging environment Docker builds failing — npm install timeout on internal registry",
        "rca": "Internal npm registry SSL certificate renewed with new CA. Docker build uses cached CA bundle that doesn't include new CA.",
        "resolution": "Updated Docker base image with new CA certificates. Added registry CA to build args. CI/CD pipeline updated.",
        "confidence": 0.95, "approval": False, "approved": None, "jira_key": None,
        "events": [
            ("Triage Agent", "Classified as P3. Dev tooling issue. Staging deployments blocked. Production not affected.", "Local File"),
            ("Telemetry Agent", "CI/CD logs show npm ERR! UNABLE_TO_VERIFY_LEAF_SIGNATURE. Started after registry cert renewal.", "Splunk MCP"),
            ("Codebase Agent", "Identified INFRA issue. Dockerfile uses node:18-alpine with outdated ca-certificates. Registry CA changed.", "GitHub MCP"),
            ("Resolution Agent", "Base image updated. CA added to build. Auto-remediated. Confidence: 95%.", "Jira + Outlook MCP"),
        ]
    },
    {
        "id": "INC-I7JF6520", "source": "slack", "severity": "P3", "status": "Processing", "issue_type": None,
        "desc": "Mobile app push notifications delayed by 10-30 minutes — Firebase Cloud Messaging latency spike",
        "rca": "", "resolution": "", "confidence": 0.0, "approval": False, "approved": None, "jira_key": None,
        "events": [
            ("Triage Agent", "Classified as P3. Mobile notification delays. Not blocking. User experience degradation. 34 support tickets.", "Email MCP"),
        ]
    },
]


# ── Insert all scenarios ─────────────────────────────────────────

base_time = datetime.now() - timedelta(hours=24)

for i, s in enumerate(SCENARIOS):
    created = (base_time + timedelta(hours=i * 1.2)).isoformat()
    resolved = (base_time + timedelta(hours=i * 1.2 + 0.5)).isoformat() if "Resolved" in s["status"] else None

    execute(
        """INSERT INTO SP_INCIDENTS 
           (incident_id, scenario_id, source, raw_description, status, severity, issue_type,
            root_cause_analysis, suggested_resolution, confidence_score,
            requires_human_approval, human_approved, jira_ticket_key, errors, created_at, resolved_at)
           VALUES (:id, :scenario_id, :source, :desc, :status, :severity, :issue_type,
                   :rca, :resolution, :confidence, :approval, :approved, :jira_key, :errors, :created, :resolved)""",
        {
            "id": s["id"],
            "scenario_id": f"scenario_{i+1}",
            "source": s["source"],
            "desc": s["desc"],
            "status": s["status"],
            "severity": s["severity"],
            "issue_type": s["issue_type"],
            "rca": s["rca"],
            "resolution": s["resolution"],
            "confidence": s["confidence"],
            "approval": 1 if s["approval"] else 0,
            "approved": 1 if s["approved"] else (0 if s["approved"] is False else None),
            "jira_key": s.get("jira_key"),
            "errors": "[]",
            "created": created,
            "resolved": resolved,
        }
    )
    
    # Insert agent reasoning events
    for j, (agent, action, source) in enumerate(s["events"]):
        event_time = (base_time + timedelta(hours=i * 1.2, minutes=j * 2 + 1)).isoformat()
        execute(
            """INSERT INTO SP_AGENT_EVENTS (incident_id, agent, action, source, created_at)
               VALUES (:id, :agent, :action, :source, :created)""",
            {"id": s["id"], "agent": agent, "action": action, "source": source, "created": event_time}
        )
    
    print(f"  [OK] {s['id']} [{s['severity']}] {s['status']}: {s['desc'][:60]}...")

print(f"\nSeeded {len(SCENARIOS)} incidents with {sum(len(s['events']) for s in SCENARIOS)} agent events into the database.")
