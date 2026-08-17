from P4PCore.event.GossipRecvedEvent import GossipRecvedEvent
from P4PCore.model.NodeIdentify import NodeIdentify

from P4PNodeGossiper.util.NodeIdentifyConverter import bytesToNodeIdentify

class NodeGossipRecvedEvent(GossipRecvedEvent):
    @property
    def recvedNode(self) -> NodeIdentify | None:
        return bytesToNodeIdentify(self._gossipContent)