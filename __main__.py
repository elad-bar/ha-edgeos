import asyncio
import logging
from custom_components.edgeos.clients.web_login import EdgeOSWebLogin

logging.basicConfig(filename="log.txt", filemode="a", level="DEBUG")


loop = asyncio.get_event_loop()


class Test:
    def __init__(self):
        self._instance = None

    async def load(self):
        self._instance = EdgeOSWebLogin("ubnt.baru.sh", "smartbar", "Windows!0")
        print(self._instance.login_resp())


if __name__ == "__main__":
    t = Test()
    loop.run_until_complete(t.load())





