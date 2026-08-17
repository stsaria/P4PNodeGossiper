from P4PCore.event.GossipDeletedByGcEvent import GossipDeletedByGcEvent
from P4PCore.model.NodeIdentify import NodeIdentify

from P4PNodeGossiper.util.NodeIdentifyConverter import bytesToNodeIdentify

class NodeGossipDeletedByGcEvent(GossipDeletedByGcEvent):
    @property
    def deletedNode(self) -> NodeIdentify | None:
        return bytesToNodeIdentify(self._gossipContent)