# CRITICAL: Initialize telemetry BEFORE importing AI frameworks
from sap_cloud_sdk.aicore import set_aicore_config
from sap_cloud_sdk.core.telemetry import auto_instrument

set_aicore_config()
auto_instrument()

import logging
import os
from dotenv import load_dotenv

# Load .env file so all environment variables (SMTP, alert recipients, etc.) are available
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'), override=False)

import click
import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill

from agent_executor import AgentExecutor
from aicore_config import log_aicore_status
from opentelemetry.instrumentation.starlette import StarletteInstrumentor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "5000"))


@click.command()
@click.option("--host", default=HOST)
@click.option("--port", default=PORT)
def main(host: str, port: int):
    # ââ Startup credential check ââââââââââââââââââââââââââââââââââââââââââââââ
    log_aicore_status()
    # âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

    skill = AgentSkill(
        id="geopolitical-risk-agent",
        name="Geopolitical Risk Intelligence Agent",
        description="Monitors real-time conflict signals from GDELT and NewsAPI, correlates them with SAP supplier and purchase-order data, scores supply-chain risk, and surfaces actionable alerts for procurement teams.",
        tags=["geopolitical", "risk", "supply-chain", "intelligence", "procurement"],
        examples=[
            "Run a geopolitical risk scan for the Middle East and Eastern Europe",
            "Which of our suppliers are at risk due to current conflict events?",
            "Show me High and Critical risk events from the last 6 hours",
            "Create SAP procurement tasks for all Critical severity events today",
        ],
    )
    agent_card = AgentCard(
        name="Geopolitical Risk Intelligence Agent",
        description="Real-time geopolitical risk intelligence agent. Integrates GDELT and NewsAPI conflict signals with SAP S/4HANA supplier and purchase-order data to score supply-chain disruption risk and trigger automated alerts and SAP tasks.",
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
    StarletteInstrumentor().instrument_app(app)

    logger.info(f"Starting A2A server at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
