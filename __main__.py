import asyncio
import logging
import time
from custom_components.edgeos import EdgeOS

from custom_components.edgeos.const import SCAN_INTERVAL

logging.basicConfig(filename="log.txt", filemode="a", level="DEBUG")


loop = asyncio.get_event_loop()


class Test:
    def __init__(self):
        self._instance = None

    async def load(self):
        self._instance = EdgeOS(None, "", "", "", True, ["eth0"], ["device"], "M",
                                SCAN_INTERVAL, True)

    async def refresh(self):
        while True:
            await self._instance.refresh()

            time.sleep(20)


if __name__ == "__main__":
    t = Test()
    loop.run_until_complete(t.load())
    loop.run_until_complete(t.refresh())





