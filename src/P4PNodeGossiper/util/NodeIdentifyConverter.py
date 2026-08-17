import socket
from socket import AF_INET6, AF_INET

from P4PCore.model.HashableEd25519PublicKey import HashableEd25519PublicKey
from P4PCore.util.BytesCoverter import *
from P4PCore.model.NodeIdentify import NodeIdentify
from P4PCore.util import BytesSplitter
from P4PCore.protocol.Protocol import SecurePacketElementSize

from P4PNodeGossiper.protocol.Protocol import NodeGossiperPacketElementSize

def nodeIdentifyToBytes(nodeIdentify:NodeIdentify) -> bytes:
    addrFamilyB = itob(
        addrFamily := (AF_INET6 if ":" in (ip := nodeIdentify.ip) else AF_INET),
        NodeGossiperPacketElementSize.IP_ADDR_FAMILY
    )
    ipB = socket.inet_pton(addrFamily, ip)
    return (
        addrFamilyB
        +ipB
        +b"\x00"*(NodeGossiperPacketElementSize.IP-len(ipB))
        +itob(nodeIdentify.port, NodeGossiperPacketElementSize.PORT)
        +nodeIdentify.hashableEd25519PublicKey.publicKeyBytes
    )
def bytesToNodeIdentify(nodeIdentifyB:bytes) -> NodeIdentify | None:
    addrFamillyB, ipB, portB, pubKeyB = BytesSplitter.split(
        nodeIdentifyB,
        NodeGossiperPacketElementSize.IP_ADDR_FAMILY,
        NodeGossiperPacketElementSize.IP,
        NodeGossiperPacketElementSize.PORT,
        SecurePacketElementSize.ED25519_PUBLIC_KEY
    )
    addrFamilly = btoi(addrFamillyB)
    if addrFamilly == AF_INET:
        ipSize = NodeGossiperPacketElementSize.IPV4
    elif addrFamilly == AF_INET6:
        ipSize = NodeGossiperPacketElementSize.IPV6
    else:
        return

    ip = socket.inet_ntop(addrFamilly, ipB[:ipSize])
    port = btoi(portB)
    pubKey = HashableEd25519PublicKey(pubKeyB)
    return NodeIdentify(ip=ip, port=port, hashableEd25519PublicKey=pubKey)
