import os
import asyncio
import pytest
from unittest.mock import patch

from P4PCore.P4PRunner import P4PRunner
from P4PCore.model.NodeIdentify import NodeIdentify
from P4PCore.model.HashableEd25519PublicKey import HashableEd25519PublicKey

from P4PNodeGossiper.NodeGossiper import *
from P4PNodeGossiper.manager.NodeStorage import NodeStorage
from P4PNodeGossiper.event.NodeGossipRecvedEvent import NodeGossipRecvedEvent
from P4PNodeGossiper.event.NodeGossipDeletedByGcEvent import NodeGossipDeletedByGcEvent
from P4PNodeGossiper.util.NodeIdentifyConverter import nodeIdentifyToBytes


def _makeNode(port: int = 12345, ip: str = "127.0.0.1") -> NodeIdentify:
    return NodeIdentify(
        ip=ip,
        port=port,
        hashableEd25519PublicKey=HashableEd25519PublicKey(os.urandom(32)),
    )

class TestNodeGossiper:
    @pytest.mark.asyncio
    async def testCreateStartsEmptyWhenStorageIsEmpty(self):
        runner = await P4PRunner.create()
        nodeGossiper = await NodeGossiper.create(runner)

        assert await nodeGossiper.getNodeIdentifies() == set()
        assert await nodeGossiper._gossiper.getAllGossipData() == []

    @pytest.mark.asyncio
    async def testAddNode(self):
        runner = await P4PRunner.create()
        nodeGossiper = await NodeGossiper.create(runner)
        await runner.begin()

        node = _makeNode()
        assert await nodeGossiper.addNode(node)
        assert node in await nodeGossiper.getNodeIdentifies()
        assert nodeIdentifyToBytes(node) in await nodeGossiper._gossiper.getAllGossipData()

    @pytest.mark.asyncio
    async def testAddNodeDuplicateReturnsFalse(self):
        runner = await P4PRunner.create()
        nodeGossiper = await NodeGossiper.create(runner)
        await runner.begin()

        node = _makeNode()
        assert await nodeGossiper.addNode(node)
        assert not await nodeGossiper.addNode(node)
        assert len(await nodeGossiper.getNodeIdentifies()) == 1

    @pytest.mark.asyncio
    async def testAddNodeRollsBackStorageWhenGossiperIsFull(self):
        runner = await P4PRunner.create()
        nodeGossiper = await NodeGossiper.create(runner, maximumNodesCount=1)
        await runner.begin()

        firstNode = _makeNode()
        secondNode = _makeNode(port=11235)

        assert await nodeGossiper.addNode(firstNode)
        assert not await nodeGossiper.addNode(secondNode)

        nodeIdentifies = await nodeGossiper.getNodeIdentifies()
        assert firstNode in nodeIdentifies
        assert secondNode not in nodeIdentifies

    @pytest.mark.asyncio
    async def testDeleteNode(self):
        runner = await P4PRunner.create()
        nodeGossiper = await NodeGossiper.create(runner)
        await runner.begin()

        node = _makeNode()
        await nodeGossiper.addNode(node)

        assert await nodeGossiper.deleteNode(node)
        assert node not in await nodeGossiper.getNodeIdentifies()
        assert nodeIdentifyToBytes(node) not in await nodeGossiper._gossiper.getAllGossipData()

    @pytest.mark.asyncio
    async def testDeleteNodeNotPresentReturnsFalse(self):
        runner = await P4PRunner.create()
        nodeGossiper = await NodeGossiper.create(runner)
        await runner.begin()

        node = _makeNode()
        assert not await nodeGossiper.deleteNode(node)

    @pytest.mark.asyncio
    async def testOnNodeGossipRecvedAddsValidNodeToStorage(self):
        runner = await P4PRunner.create()
        nodeGossiper = await NodeGossiper.create(runner)
        await runner.begin()

        node = _makeNode()
        event = NodeGossipRecvedEvent(nodeIdentifyToBytes(node), ("127.0.0.1", 9999))
        await nodeGossiper.onNodeGossipRecved(event)

        assert node in await nodeGossiper.getNodeIdentifies()

    @pytest.mark.asyncio
    async def testOnNodeGossipRecvedIgnoresInvalidData(self):
        runner = await P4PRunner.create()
        nodeGossiper = await NodeGossiper.create(runner)
        await runner.begin()

        garbage = os.urandom(GOSSIP_SIZE)
        event = NodeGossipRecvedEvent(garbage, ("127.0.0.1", 9999))
        await nodeGossiper.onNodeGossipRecved(event)

        assert await nodeGossiper.getNodeIdentifies() == set()

        await runner.end()

    @pytest.mark.asyncio
    async def testOnNodeGossipDeletedByGcRemovesNodeFromStorage(self):
        runner = await P4PRunner.create()
        nodeGossiper = await NodeGossiper.create(runner)
        await runner.begin()

        node = _makeNode()
        await nodeGossiper.addNode(node)

        event = NodeGossipDeletedByGcEvent(nodeIdentifyToBytes(node))
        await nodeGossiper.onNodeGossipDeletedByGc(event)

        assert node not in await nodeGossiper.getNodeIdentifies()

        await runner.end()

    @pytest.mark.asyncio
    async def testOnNodeGossipDeletedByGcIgnoresInvalidData(self):
        runner = await P4PRunner.create()
        nodeGossiper = await NodeGossiper.create(runner)
        await runner.begin()

        node = _makeNode()
        await nodeGossiper.addNode(node)

        garbage = b"\xff\xff\xff\xff" + os.urandom(60)
        event = NodeGossipDeletedByGcEvent(garbage)
        await nodeGossiper.onNodeGossipDeletedByGc(event)

        # Storage should be untouched since the payload didn't decode.
        assert node in await nodeGossiper.getNodeIdentifies()

        await runner.end()

    @pytest.mark.asyncio
    async def testEndToEndGossipPropagatesNodeBetweenPeers(self):
        runner = await P4PRunner.create()
        nodeGossiper = await NodeGossiper.create(runner)
        await runner.begin()
        await nodeGossiper._gossiper.begin()

        runner2 = await P4PRunner.create()
        nodeGossiper2 = await NodeGossiper.create(runner2)
        await runner2.begin()
        await nodeGossiper2._gossiper.begin()

        await asyncio.sleep(0)

        node = _makeNode()
        await nodeGossiper2.addNode(node)

        nodeGossiper2._gossiper._gossip(
            runner._net._protocolV4.transport.get_extra_info("sockname"),
            nodeIdentifyToBytes(node)
        )

        await asyncio.sleep(0.1)

        assert node in await nodeGossiper.getNodeIdentifies()