import asyncio

from P4PCore.manager.SimpleImpls import SimpleKVManager
from P4PCore.P4PRunner import P4PRunner

class AlivedNodes:
    def __init__(self, runner:P4PRunner, pingPongTimeoutSeconds:float, aliveTimeSeconds:float):
        self._runner:P4PRunner = runner
        self._manager:SimpleKVManager[tuple[str, int], float] = SimpleKVManager()
        self._aliveTimeSeconds:float = aliveTimeSeconds
        self._pingPongTimeoutSeconds:float = pingPongTimeoutSeconds

    async def checkAndUpdateAlive(self, addr:tuple[str, int]) -> bool:
        """
        Check if a node is alive and update its status.

        :param addr: The address of the node to check.
        :return: True if the node is alive; otherwise False.
        """
        now = asyncio.get_event_loop().time()
        if not ((timestamp := await self._manager.get(addr)) is None):
            if (now - timestamp) <= self._aliveTimeSeconds:
                return True
        if await self._runner.pingPongNet.ping(addr, timeoutSecs=self._pingPongTimeoutSeconds):
            await self._manager.put(addr, now)
            return True
        return False