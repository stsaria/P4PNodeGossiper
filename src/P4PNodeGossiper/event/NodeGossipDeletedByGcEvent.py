from P4PCore.event.GossipDeletedByGcEvent import GossipDeletedByGcEvent
from P4PCore.model.NodeIdentify import NodeIdentify

from P4PNodeGossiper.util.NodeIdentifyConverter import bytesToNodeIdentify

class NodeGossipDeletedByGcEvent(GossipDeletedByGcEvent):
    @property
    def deletedNode(self) -> NodeIdentify | None:
        """
        Returns the identifying information of the node deleted by GC.

        The gossip payload is converted into a NodeIdentify instance so the
        details of the deleted node can be retrieved.
        """
        return bytesToNodeIdentify(self._gossipContent)