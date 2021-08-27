import structlog
from reporting.report import *


def handler(event, context):
    logger = structlog.get_logger()
    logger.info("starting")
    client = ReportingClient()
    client.handle()
