from importlib.metadata import version
import logging
import uuid
from uuid import UUID

from P4PCore.P4PRunner import Logger, P4PRunner
from P4PCore.impledPlugin.Gossiper import Gossiper
from P4PCore.protocol.Protocol import SecurePacketElementSize
from P4PCore.manager.Events import EventListener
from P4PCore.model.NodeIdentify import NodeIdentify
from P4PCore.event.CalledBeginFunctionOfRunnerEvent import CalledBeginFunctionOfRunnerEvent
from P4PCore.event.CalledEndFunctionOfRunnerEvent import CalledEndFunctionOfRunnerEvent

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
    A gossiper plugin that manages the gossiping of node information
    in a P2P network.
    """
    _nodeStorage:NodeStorage
    _gossiper:Gossiper
    _logger:Logger

    @classmethod
    async def create(
        cls,
        runner:P4PRunner,
        gossipTTLSeconds:int=5,
        syncNodeCountPerOneTime:int=5,
        syncIntervalSeconds:float=5,
        maximumNodesCount:int=100
    ) -> "NodeGossiper":
        """
        Create a new NodeGossiper instance.

        :param runner: The P4PRunner instance to use for networking and
            event management.
        :param gossipTTLSeconds: The time-to-live for each node gossip
            message in seconds.
        :param syncNodeCountPerOneTime: The maximum number of nodes to
            synchronize with in one synchronization.
        :param syncIntervalSeconds: The interval between synchronization
            attempts in seconds.
        :param maximumNodesCount: The maximum number of nodes to store.
        :return: An initialized NodeGossiper instance.
        """
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
            syncNodeCountPerOneTime=syncNodeCountPerOneTime,
            syncIntervalSeconds=syncIntervalSeconds,
            maximumSavedDataCount=maximumNodesCount,
            requiredGossip=nodeIdentifyToBytes(
                NodeIdentify(
                    ip="",
                    port=0,
                    hashableEd25519PublicKey=runner.ed25519Signer.publicKey
                )
            )
        )

        inst._logger = await runner.getLogger("NodeGossiper")
        await runner.eventsManager.registerListener(inst)

        return inst

    async def addNode(self, nodeIdentify:NodeIdentify) -> bool:
        """
        Add a node to the gossiper and node storage.

        If adding the gossip fails after the node has been added to storage,
        the storage operation is rolled back.

        :param nodeIdentify: The NodeIdentify object of the node to add.
        :return: True if the node was added successfully; otherwise False.
        """
        if not await self._nodeStorage.addNode(nodeIdentify):
            self._logger.debug(
                "Node already exists. nodeId:%s",
                nodeIdentifyToBytes(nodeIdentify).hex()
            )
            return False

        if not await self._gossiper.addGossip(
            nodeIdentifyToBytes(nodeIdentify),
            nodeIdentify.addr
        ):
            await self._nodeStorage.removeNode(nodeIdentify)
            self._logger.warning(
                "Failed to add node to gossiper, rolled back. nodeId:%s",
                nodeIdentifyToBytes(nodeIdentify).hex()
            )
            return False

        return True

    async def deleteNode(self, nodeIdentify:NodeIdentify) -> bool:
        """
        Remove a node from the gossiper and node storage.

        :param nodeIdentify: The NodeIdentify object of the node to remove.
        :return: True if the node was removed from both storage and the
            gossiper; otherwise False.
        """
        deletedFromStorage = await self._nodeStorage.removeNode(nodeIdentify)
        deletedFromGossiper = await self._gossiper.deleteGossip(
            nodeIdentifyToBytes(nodeIdentify)
        )

        if deletedFromStorage and deletedFromGossiper:
            self._logger.info(
                "Node deleted. nodeId:%s",
                nodeIdentifyToBytes(nodeIdentify).hex()
            )
            return True
        else:
            self._logger.warning(
                "Partial deletion. nodeId:%s storage:%s gossiper:%s",
                nodeIdentifyToBytes(nodeIdentify).hex(),
                deletedFromStorage,
                deletedFromGossiper
            )
            return False

    async def getNodeIdentifies(self) -> set[NodeIdentify]:
        """
        Return all NodeIdentify objects currently stored by the gossiper.

        :return: A set of NodeIdentify objects.
        """
        return await self._nodeStorage.getNodeIdentifies()

    async def getAddrs(self) -> set[NodeIdentify]:
        """
        Return the addresses of all nodes currently stored by the gossiper.

        :return: A collection of node addresses.
        """
        return await self._nodeStorage.getAddrs()

    @EventListener
    async def onNodeGossipRecved(
        self,
        event:NodeGossipRecvedEvent
    ) -> None:
        """
        Handle a received node gossip event.

        If the received gossip contains only the sender's public key,
        the sender's address is taken from the received event address.

        :param event: The NodeGossipRecvedEvent containing the received
            node gossip and sender address.
        :return: None.
        """
        recvedNode = event.recvedNode

        if recvedNode is None:
            self._logger.warning(
                "Recved invalid node gossip. gossipContent:%s",
                str(event._gossipContent)
            )
            return

        elif not (recvedNode.ip and recvedNode.port):
            # sender's info
            recvedNode = NodeIdentify(
                ip=event.addr[0],
                port=event.addr[1],
                hashableEd25519PublicKey=recvedNode.hashableEd25519PublicKey
            )

        await self.addNode(recvedNode)

        self._logger.debug(
            "Node gossip recved. and try to add nodeId:%s",
            nodeIdentifyToBytes(recvedNode).hex()
        )

    @EventListener
    async def onNodeGossipDeletedByGc(
        self,
        event:NodeGossipDeletedByGcEvent
    ) -> None:
        """
        Handle a node gossip garbage-collection event.

        If the deleted gossip cannot be converted to a valid NodeIdentify,
        the event is ignored.

        :param event: The NodeGossipDeletedByGcEvent containing the deleted
            node gossip.
        :return: None.
        """
        deletedNode = event.deletedNode

        if deletedNode is None:
            self._logger.warning(
                "Deleted invalid node gossip. gossipContent:%s",
                str(event._gossipContent)
            )
            return

        await self._nodeStorage.removeNode(deletedNode)

        self._logger.debug(
            "Node gossip deleted by GC. nodeId:%s",
            nodeIdentifyToBytes(deletedNode).hex()
        )

    async def sync(self) -> None:
        """
        Synchronize node gossip with other nodes in the network.

        This performs a single synchronization operation using the underlying
        Gossiper.

        :return: None.
        """
        await self._gossiper.sync()

    @EventListener
    async def onBegin(
        self,
        _:CalledBeginFunctionOfRunnerEvent
    ) -> None:
        """
        Handle the runner begin event and start the gossip synchronization
        task.

        :param _: The CalledBeginFunctionOfRunnerEvent.
        :return: None.
        """
        self._logger.info("NodeGossiper sync task starting.")
        await self._gossiper.begin()

    @EventListener
    async def onEnd(
        self,
        _:CalledEndFunctionOfRunnerEvent
    ) -> None:
        """
        Handle the runner end event and stop the gossip synchronization task.

        :param _: The CalledEndFunctionOfRunnerEvent.
        :return: None.
        """
        self._logger.info("NodeGossiper sync task stopping.")
        await self._gossiper.end()