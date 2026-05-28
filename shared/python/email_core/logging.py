import logging
import os


def configure_logging(service_name: str) -> None:
    """Configure consistent JSON-like logs for all services."""
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s service=%(service)s %(message)s",
    )

    old_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):  # type: ignore[no-untyped-def]
        record = old_factory(*args, **kwargs)
        if not hasattr(record, "service"):
            record.service = service_name
        return record

    logging.setLogRecordFactory(record_factory)

