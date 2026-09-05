"""Command-line entry point for the Raspberry Pi display agent."""

from __future__ import annotations

import argparse
import logging

from . import __version__
from .agent import InkyAgent
from .config import AgentSettings
from .hardware import FixedE673Driver, NoopDisplayDriver, SerializedDisplayWorker
from .spool import AgentSpool
from .systemd import SystemdNotifier
from .transport import HostClient


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Inky E673 Raspberry Pi display agent")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--once", action="store_true", help="reconcile once and exit")
    args = parser.parse_args()

    settings = AgentSettings.from_env()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logger = logging.getLogger(__name__)
    logger.info(
        "starting fixed E673 Pi agent",
        extra={
            "display_id": settings.display_id,
            "server_url": settings.base_url,
            "hardware_enabled": settings.hardware_enabled,
        },
    )

    driver = FixedE673Driver() if settings.hardware_enabled else NoopDisplayDriver()
    client = HostClient(settings)
    notifier = SystemdNotifier()
    try:
        agent = InkyAgent(settings, client, AgentSpool(settings.data_dir), SerializedDisplayWorker(driver))
        notifier.ready()
        if args.once:
            agent.run_once()
        else:
            agent.run_forever(notifier)
    finally:
        client.close()
