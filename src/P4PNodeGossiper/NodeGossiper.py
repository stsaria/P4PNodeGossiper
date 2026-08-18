from importlib.metadata import version
import uuid
from uuid import UUID

from P4PCore.P4PRunner import Logger, P4PRunner
from P4PCore.impledPlugin.Gossiper import Gossiper
from P4PCore.protocol.Protocol import SecurePacketElementSize
from P4PCore.manager.Events import EventListener
from P4PCore.model.NodeIdentify import NodeIdentify

from P4PNodeGossiper.manager.NodeStorage import NodeStorage
from P4PNodeGossiper.event.NodeGossipDeletedByGcEvent import NodeGossipDeletedByGcEvent
from P4PNodeGossiper.event.NodeGossipRecvedEvent import NodeGossipRecvedEvent
from P4PNodeGossiper.protocol.Protocol import *
from P4PNodeGossiper.util.NodeIdentifyConverter import nodeIdentifyToBytes

BASE_PLUGIN_UUID_HEX = "27416bf84dbd4a448cc12adf238aa5f6"
PROTOCOL_VERSION = "1"
PLUGIN_UUID = uuid.uuid5(UUID(hex=BASE_PLUGIN_UUID_HEX), PROTOCOL_VERSION)

GOSSIP_SIZE =(
    NodeGossiperPacketElementSize.IP_ADDR_FAMILY
    +NodeGossiperPacketElementSize.IP
    +NodeGossiperPacketElementSize.PORT
    +SecurePacketElementSize.ED25519_PUBLIC_KEY
)

class NodeGossiper:
    """
    A gossiper plugin that manages the gossiping of node information in a p2p network.
    """
    _nodeStorage:NodeStorage
    _gossiper:Gossiper
    _logger:Logger

    @classmethod
    async def create(
        cls,
        runner:P4PRunner,
        gossipTTLSeconds:int=5,
        syncPeerCountPerOneTime: int = 5,
        syncIntervalSeconds: float = 5,
        maximumNodesCount: int = 100
    ) -> "NodeGossiper":
        inst = cls()

        inst._nodeStorage = NodeStorage()
        inst._gossiper = await Gossiper.create(
            runner,
            PLUGIN_UUID,
            GOSSIP_SIZE,
            MAXIMUM_GOSSIP_COUNT_PER_MESSAGE,
            inst._nodeStorage.getAddrs,
            NodeGossipRecvedEvent,
            NodeGossipDeletedByGcEvent,
            gossipTTLSeconds=gossipTTLSeconds,
            syncPeerCountPerOneTime=syncPeerCountPerOneTime,
            syncIntervalSeconds=syncIntervalSeconds,
            maximumSavedDataCount=maximumNodesCount
        )
        inst._logger = await runner.getLogger("NodeGossiper")

        await runner.eventsManager.registerListener(inst)
        
        return inst
    
    async def addNode(self, nodeIdentify:NodeIdentify) -> bool:
        """
        Adds a node to the gossiper and the storage.
        """
        addedToStorage = await self._nodeStorage.addNode(nodeIdentify)
        if not addedToStorage:
            return False
        addedToGossiper = await self._gossiper.addGossip(nodeIdentifyToBytes(nodeIdentify))
        if not addedToGossiper:
            await self._nodeStorage.removeNode(nodeIdentify)
            return False
        return True
    async def deleteNode(self, nodeIdentify:NodeIdentify) -> bool:
        """
        Deletes a node from the gossiper and the storage.
        """
        deletedFromStorage = await self._nodeStorage.removeNode(nodeIdentify)
        deletedFromGossiper = await self._gossiper.deleteGossip(nodeIdentifyToBytes(nodeIdentify))
        return deletedFromStorage and deletedFromGossiper
    
    async def getNodeIdentifies(self) -> set[NodeIdentify]:
        """
        Returns a list of all the nodes in the gossiper.
        """
        return await self._nodeStorage.getNodeIdentifies()

    async def getAddrs(self) -> set[NodeIdentify]:
        """
        Returns a list of all the addrs of the nodes in the gossiper.
        """
        return await self._nodeStorage.getAddrs()
    
    @EventListener
    async def onNodeGossipRecved(self, event:NodeGossipRecvedEvent) -> None:
        """
        Event listener for when a node gossip is received.
        """
        recvedNode = event.recvedNode
        if recvedNode is None:
            self._logger.warning(f"Recved invalid node gossip. gossipContent:{str(event._gossipContent)}")
            return
        await self._nodeStorage.addNode(recvedNode)
    @EventListener
    async def onNodeGossipDeletedByGc(self, event:NodeGossipDeletedByGcEvent) -> None:
        """
        Event listener for when a node gossip is deleted by the garbage collector.
        """
        deletedNode = event.deletedNode
        if deletedNode is None:
            self._logger.warning(f"Deleted invalid node gossip. gossipContent:{str(event._gossipContent)}")
            return
        await self._nodeStorage.removeNode(deletedNode)

    async def sync(self) -> None:
        """
        Synchronize the gossiper with peers.
        This method is called periodically to ensure that the gossiper has the latest gossip messages from other peers in the network.
        """
        await self._gossiper.sync()

    async def begin(self) -> None:
        """
        Start the gossiper's synchronization task.
        If you want to see details about the gossiper, you should only call NodeGossiper.sync.
        """
        await self._gossiper.begin()

    async def end(self) -> None:
        """
        End the gossiper's synchronization task.
        """
        await self._gossiper.end()