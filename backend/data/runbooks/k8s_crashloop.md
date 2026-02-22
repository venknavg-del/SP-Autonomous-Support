# Runbook: Kubernetes Pod CrashLoopBackOff

## Symptoms
- Deployments showing `CrashLoopBackOff` status in Kubernetes cluster.
- Pods restarting frequently (e.g., every 2 minutes).
- Liveness or Readiness probes failing consistently in Kubernetes events.

## Root Cause
Common causes include process crashes upon startup (OOM), missing environment variables, failing health checks due to long startup times, or corrupted volume mounts.

## Resolution Steps
1. **Immediate Mitigation:**
   - If caused by probe timeouts, increase initial delay. Run: `kubectl edit deployment <deployment-name>` and increase `initialDelaySeconds` and `timeoutSeconds`.
   - Consider adding a `startupProbe` if the application is known for slow initialization.
2. **Investigation:**
   - Check pod logs from previous crashed instance: `kubectl logs <pod-name> --previous`
   - Describe pod to see event history: `kubectl describe pod <pod-name>`
3. **Escalation:**
   - If the crash is due to OOMKilled, escalate to the infrastructure team to review memory limits and the dev team to profile for memory leaks.
