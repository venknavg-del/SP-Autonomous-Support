# Runbook: Redis Cache Eviction & Hit Ratio Drop

## Symptoms
- Redis cache hit ratio drops significantly (e.g., from 95% to < 50%).
- Database load spikes proportionally.
- Redis reports OOM (Out of Memory) or high `evicted_keys` per second.

## Root Cause
Usually triggered by incorrect cache policies, massive influx of new unique keys, or changes to the `maxmemory-policy` setting (e.g., set to `noeviction` instead of `allkeys-lru`).

## Resolution Steps
1. **Immediate Mitigation:**
   - Verify Redis memory policy via CLI: `redis-cli INFO memory | grep maxmemory_policy`
   - If policy is incorrect, dynamically update it to LRU: `redis-cli CONFIG SET maxmemory-policy allkeys-lru`
   - Consider flushing stale keys or specific bloated patterns if an upstream bug caused cache pollution.
2. **Investigation:**
   - Check which keys are consuming the most memory using `redis-cli --bigkeys` or similar tools.
   - Investigate recent application deployments that might have altered caching behavior.
3. **Capacity Planning:**
   - If legitimate traffic caused the growth, plan for scaling up the Redis instance.
