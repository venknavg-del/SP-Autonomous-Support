# Runbook: Database Connection Pool Exhaustion

## Symptoms
- HikariPool-1 reporting 100% utilization in logs
- "Connection timeout" errors in Application logs
- High latency on database queries (p99 > 2000ms)
- Application nodes returning HTTP 500 or 503 errors

## Root Cause
Often caused by sudden spikes in traffic, long-running transactions blocking connections, or a failure in the auto-scaling logic resulting in insufficient active connection pools.

## Resolution Steps
1. **Immediate Mitigation:**
   - Increase the maximum pool size dynamically. Connect to the target pod and run: `app-cli config set db.pool.max=100`
   - Trigger the Terraform auto-scaling rule manually to adjust expected load: `terraform apply -target=module.db_cluster -var="pool_size=100" -auto-approve`
2. **Investigation:**
   - Check Splunk logs for slow queries: `index=prod sourcetype=db_logs duration>500`
   - Review active database locks in the admin console.
3. **Escalation:**
   - If issue persists after pool size increase, escalate to the DBA team immediately.
