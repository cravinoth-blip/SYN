import logging
import os
import time

from redis import Redis
from rq import Worker


logging.basicConfig(level=logging.INFO)


def main() -> None:
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    redis = Redis.from_url(redis_url)
    worker = Worker(["generation", "export"], connection=redis)
    logging.info("Starting 7Cs worker on queues: generation, export")
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover - keeps container logs useful in early setup
        logging.exception("Worker failed to start: %s", exc)
        time.sleep(5)
        raise

