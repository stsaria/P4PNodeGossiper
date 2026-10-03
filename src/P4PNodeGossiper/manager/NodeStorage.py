from P4PCore.manager.SimpleImpls import SimpleSetManager
from P4PCore.model.NodeIdentify import NodeIdentify

class NodeStorage:
    def __init__(self):
        self._manager:SimpleSetManager[NodeIdentify] = SimpleSetManager()

    async def getAddrs(self) -> set[tuple[str, int]]:
        """
        Return the addresses of all nodes currently stored.

        :return: A list of node addresses.
        """
        nodes = await self._manager.getAll()

        return [node.addr for node in nodes]

    async def addNode(self, node:NodeIdentify) -> bool:
        """
        Add a node to the storage.

        :param node: The NodeIdentify object to add.
        :return: True if the node was added successfully; otherwise False.
        """
        return await self._manager.add(node)

    async def removeNode(self, node:NodeIdentify) -> bool:
        """
        Remove a node from the storage.

        :param node: The NodeIdentify object to remove.
        :return: True if the node was removed successfully; otherwise False.
        """
        return await self._manager.remove(node)

    async def getNodeIdentifies(self) -> set[NodeIdentify]:
        """
        Return all NodeIdentify objects currently stored.

        :return: A list of NodeIdentify objects.
        """
        return await self._manager.getAll()