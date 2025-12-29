"""
Maestra Backend - Observability Module
Metrics, JSON logging, and Slack alerts
"""

import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import httpx

# Configuration
METRICS_LOG_PATH = Path.home() / ".8825" / "maestra_metrics.jsonl"
SLACK_WEBHOOK_URL = os.getenv("MAESTRA_SLACK_WEBHOOK_URL", "")
SLACK_ALERTS_ENABLED = bool(SLACK_WEBHOOK_URL)

# Ensure metrics log directory exists
METRICS_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


@dataclass
class RequestMetrics:
    """Metrics for a single request"""
    timestamp: str
    request_id: str
    surface_id: str
    user_id: str
    conversation_id: str
    mode: str
    latency_ms: int
    status_code: int
    tokens: int
    cost_usd: float
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class SystemMetrics:
    """System-level metrics"""
    timestamp: str
    uptime_seconds: int
    total_requests: int
    total_errors: int
    avg_latency_ms: float
    total_cost_usd: float
    active_conversations: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class MetricsCollector:
    """Collect and store metrics"""
    
    def __init__(self):
        self.total_requests = 0
        self.total_errors = 0
        self.total_latency_ms = 0
        self.total_cost_usd = 0.0
        self.start_time = datetime.utcnow()
    
    def record_request(self, metrics: RequestMetrics):
        """Record a request metric"""
        self.total_requests += 1
        self.total_latency_ms += metrics.latency_ms
        self.total_cost_usd += metrics.cost_usd
        
        if metrics.status_code >= 400:
            self.total_errors += 1
        
        # Log to JSONL
        self._log_metric(metrics)
    
    def _log_metric(self, metrics: RequestMetrics):
        """Log metric to JSONL file"""
        try:
            with open(METRICS_LOG_PATH, 'a') as f:
                f.write(json.dumps(metrics.to_dict()) + '\n')
        except Exception as e:
            logging.error(f"Failed to log metric: {e}")
    
    def get_system_metrics(self, active_conversations: int) -> SystemMetrics:
        """Get system-level metrics"""
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        avg_latency = (
            self.total_latency_ms / self.total_requests
            if self.total_requests > 0
            else 0
        )
        
        return SystemMetrics(
            timestamp=datetime.utcnow().isoformat() + "Z",
            uptime_seconds=int(uptime),
            total_requests=self.total_requests,
            total_errors=self.total_errors,
            avg_latency_ms=avg_latency,
            total_cost_usd=self.total_cost_usd,
            active_conversations=active_conversations
        )


class JSONLogger:
    """JSON-formatted logging"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(name)
    
    def log_event(
        self,
        event_type: str,
        level: str = "info",
        **kwargs
    ):
        """Log structured event as JSON"""
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "logger": self.name,
            "level": level.upper(),
            "event_type": event_type,
            **kwargs
        }
        
        log_message = json.dumps(event)
        
        if level == "debug":
            self.logger.debug(log_message)
        elif level == "info":
            self.logger.info(log_message)
        elif level == "warning":
            self.logger.warning(log_message)
        elif level == "error":
            self.logger.error(log_message)
        elif level == "critical":
            self.logger.critical(log_message)


class SlackAlerter:
    """Send alerts to Slack"""
    
    def __init__(self):
        self.enabled = SLACK_ALERTS_ENABLED
        self.webhook_url = SLACK_WEBHOOK_URL
    
    async def alert(
        self,
        title: str,
        message: str,
        severity: str = "warning",
        **kwargs
    ):
        """Send alert to Slack"""
        if not self.enabled:
            return
        
        # Color based on severity
        color_map = {
            "info": "#36a64f",
            "warning": "#ff9900",
            "error": "#ff0000",
            "critical": "#8b0000"
        }
        
        payload = {
            "attachments": [
                {
                    "color": color_map.get(severity, "#808080"),
                    "title": title,
                    "text": message,
                    "fields": [
                        {
                            "title": k.replace("_", " ").title(),
                            "value": str(v),
                            "short": True
                        }
                        for k, v in kwargs.items()
                    ],
                    "footer": "Maestra Backend",
                    "ts": int(datetime.utcnow().timestamp())
                }
            ]
        }
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    self.webhook_url,
                    json=payload
                )
                response.raise_for_status()
        except Exception as e:
            logging.error(f"Failed to send Slack alert: {e}")


# Global instances
_metrics_collector: Optional[MetricsCollector] = None
_slack_alerter: Optional[SlackAlerter] = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create global metrics collector"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def get_slack_alerter() -> SlackAlerter:
    """Get or create global Slack alerter"""
    global _slack_alerter
    if _slack_alerter is None:
        _slack_alerter = SlackAlerter()
    return _slack_alerter
