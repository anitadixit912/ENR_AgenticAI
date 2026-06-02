# CRITICAL: Initialize telemetry BEFORE importing AI frameworks
import logging
import os
import sys

# Minimal logging before SDK init
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("Starting churn-prevention-agent server initialization...")

try:
    from sap_cloud_sdk.aicore import set_aicore_config
    from sap_cloud_sdk.core.telemetry import auto_instrument
    set_aicore_config()
    auto_instrument()
    logger.info("SDK initialization complete")
except Exception as _sdk_err:
    logger.warning("SDK initialization warning (non-fatal): %s", _sdk_err)

import click
import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill

from agent_executor import AgentExecutor

try:
    from opentelemetry.instrumentation.starlette import StarletteInstrumentor
    _OTEL_STARLETTE = True
except ImportError:
    _OTEL_STARLETTE = False
    logger.warning("opentelemetry-instrumentation-starlette not available, skipping OTel instrumentation")

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "5000"))

logger.info("Server will listen on %s:%d", HOST, PORT)


@click.command()
@click.option("--host", default=HOST)
@click.option("--port", default=PORT)
def main(host: str, port: int):
    logger.info("Building A2A server on %s:%d", host, port)

    skill = AgentSkill(
        id="churn-prevention-agent",
        name="churn-prevention-agent",
        description="An AI agent that detects early customer churn signals in SAP S/4HANA, scores at-risk accounts, and surfaces personalised Joule alerts to sales teams with full GDPR audit trail logging.",
        tags=["churn", "prevention", "sales", "s4hana", "joule"],
        examples=["Run the weekly churn scan for all active customers", "Which accounts are at risk of churning this week?"],
    )
    agent_card = AgentCard(
        name="churn-prevention-agent",
        description="An AI agent that detects early customer churn signals in SAP S/4HANA, scores at-risk accounts, and surfaces personalised Joule alerts to sales teams with full GDPR audit trail logging.",
        url=os.environ.get("AGENT_PUBLIC_URL", f"http://{host}:{port}/"),
        version="1.0.0",
        default_input_modes=["text", "text/plain"],
        default_output_modes=["text", "text/plain"],
        capabilities=AgentCapabilities(streaming=True, push_notifications=False),
        skills=[skill],
    )
    server = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=DefaultRequestHandler(
            agent_executor=AgentExecutor(),
            task_store=InMemoryTaskStore(),
        ),
    )
    app = server.build()

    if _OTEL_STARLETTE:
        try:
            StarletteInstrumentor().instrument_app(app)
            logger.info("OTel Starlette instrumentation applied")
        except Exception as _otel_err:
            logger.warning("OTel Starlette instrumentation failed (non-fatal): %s", _otel_err)

    logger.info("Starting A2A server at http://%s:%d", host, port)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
