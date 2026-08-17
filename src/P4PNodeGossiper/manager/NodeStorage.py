from P4PCore.manager.SimpleImpls import SimpleSetManager
from P4PCore.model.NodeIdentify import NodeIdentify

class NodeStorage:
    def __init__(self):
        self.manager:SimpleSetManager[NodeIdentify] = SimpleSetManager()
    async def getAddrs(self):
        """
        Returns a list of all the addrs of the nodes in the storage.
        """
        nodes = await self.manager.getAll()
        return [node.addr for node in nodes]
    async def addNode(self, node:NodeIdentify) -> bool:
        """
        Adds a node to the storage.
        """
        return await self.manager.add(node)
    async def removeNode(self, node:NodeIdentify) -> bool:
        """
        Removes a node from the storage.
        """
        return await self.manager.remove(node)
    async def getNodeIdentifies(self):
        """
        Returns a list of all the nodes in the storage.
        """
        return await self.manager.getAll()
    


    