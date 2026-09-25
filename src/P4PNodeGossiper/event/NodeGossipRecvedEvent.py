from P4PCore.event.GossipRecvedEvent import GossipRecvedEvent
from P4PCore.model.NodeIdentify import NodeIdentify

from P4PNodeGossiper.util.NodeIdentifyConverter import bytesToNodeIdentify

class NodeGossipRecvedEvent(GossipRecvedEvent):
    @property
    def recvedNode(self) -> NodeIdentify | None:
        """
        Returns the identifying information of the received node.

        The gossip payload is converted into a NodeIdentify instance so the
        details of the received node can be retrieved.
        """
        return bytesToNodeIdentify(self._gossipContent)