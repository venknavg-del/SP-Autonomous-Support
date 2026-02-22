"""
Splunk MCP Server — Exposes log analysis tools via FastMCP.

Tools:
  - splunk_search: Execute an SPL query and return matching logs
  - get_metrics: Fetch time-series metrics for a service/component
  - get_alert_history: Retrieve recent alerts for a service

In production, replace mock logic with Splunk SDK / REST API calls.
Requires: SPLUNK_URL, SPLUNK_API_KEY
"""

from mcp.server.fastmcp import FastMCP
import json

mcp = FastMCP("Splunk Log Server")


@mcp.tool()
def splunk_search(query: str) -> str:
    """
    Executes a Splunk Search Processing Language (SPL) query and returns matching logs.
    """
    if "PaymentService" in query or "error" in query.lower():
        return json.dumps([
            {"timestamp": "2024-05-20T10:00:01Z", "level": "ERROR", "service": "payment-svc", "message": "NullPointerException in com.company.PaymentService:145"},
            {"timestamp": "2024-05-20T10:00:03Z", "level": "ERROR", "service": "payment-svc", "message": "NullPointerException in com.company.PaymentService:145"},
            {"timestamp": "2024-05-20T10:00:05Z", "level": "WARN",  "service": "payment-svc", "message": "Transaction failed after 3 retries for user 7892"}
        ])
    elif "db" in query.lower() or "timeout" in query.lower() or "hikari" in query.lower():
        return json.dumps([
            {"timestamp": "2024-05-20T11:15:00Z", "level": "WARN",  "service": "hikaripool", "message": "HikariPool-1 - Connection is not available, request timed out after 30000ms."},
            {"timestamp": "2024-05-20T11:15:05Z", "level": "ERROR", "service": "auth-svc",   "message": "Failed to authenticate user: db connection timeout"},
            {"timestamp": "2024-05-20T11:15:08Z", "level": "ERROR", "service": "hikaripool", "message": "HikariPool-1 - Pool stats (total=100, active=100, idle=0, waiting=45)"}
        ])
    else:
        return json.dumps([{"message": "No specific errors found matching query."}])


@mcp.tool()
def get_metrics(service_name: str, metric: str = "error_rate", time_range: str = "1h") -> str:
    """
    Fetches time-series metrics for a specific service.
    Supported metrics: error_rate, latency_p99, throughput, cpu_usage, memory_usage
    """
    mock_metrics = {
        "payment-svc": {
            "error_rate":   {"unit": "%",  "values": [0.1, 0.3, 1.2, 5.8, 12.4, 18.7, 22.1]},
            "latency_p99":  {"unit": "ms", "values": [120, 145, 280, 890, 1500, 3200, 5100]},
            "throughput":   {"unit": "rps", "values": [500, 480, 420, 310, 180, 95, 40]},
        },
        "hikaripool": {
            "error_rate":   {"unit": "%",  "values": [0.0, 0.0, 2.1, 8.5, 15.0, 25.0]},
            "cpu_usage":    {"unit": "%",  "values": [45, 52, 68, 78, 85, 92]},
        }
    }

    svc = mock_metrics.get(service_name, {})
    data = svc.get(metric, {"unit": "unknown", "values": []})

    return json.dumps({
        "service": service_name,
        "metric": metric,
        "time_range": time_range,
        "unit": data["unit"],
        "datapoints": data["values"]
    }, indent=2)


@mcp.tool()
def get_alert_history(service_name: str, max_alerts: int = 5) -> str:
    """
    Retrieves recent triggered alerts for a specific service.
    Returns alert name, severity, trigger time, and status.
    """
    mock_alerts = {
        "payment-svc": [
            {"alert": "Error Rate > 5%",    "severity": "critical", "triggered": "2024-05-20T09:55:00Z", "status": "firing"},
            {"alert": "Latency P99 > 2000ms","severity": "warning",  "triggered": "2024-05-20T09:57:00Z", "status": "firing"},
            {"alert": "Throughput Drop > 50%","severity": "critical", "triggered": "2024-05-20T10:01:00Z", "status": "firing"},
        ],
        "hikaripool": [
            {"alert": "Pool Utilization > 90%",  "severity": "warning",  "triggered": "2024-05-20T11:05:00Z", "status": "resolved"},
            {"alert": "Pool Utilization > 95%",  "severity": "critical", "triggered": "2024-05-20T11:10:00Z", "status": "firing"},
            {"alert": "Connection Timeout Spike", "severity": "critical", "triggered": "2024-05-20T11:12:00Z", "status": "firing"},
        ]
    }

    alerts = mock_alerts.get(service_name, [])
    return json.dumps(alerts[:max_alerts], indent=2)


if __name__ == "__main__":
    mcp.run()
