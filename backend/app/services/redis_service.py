import logging
from typing import Optional, Any
import json

logger = logging.getLogger(__name__)

class MockRedis:
    def __init__(self):
        self.store = {}

    def setex(self, key: str, seconds: int, value: str):
        self.store[key] = value
        logger.info(f"Redis SETEX: {key} for {seconds}s")

    def get(self, key: str) -> Optional[str]:
        return self.store.get(key)

    def delete(self, key: str):
        if key in self.store:
            del self.store[key]

redis_client = MockRedis()