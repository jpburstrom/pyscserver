from osc4py3.as_eventloop import *
from osc4py3 import oscbuildparse, oscchannel
import asyncio
import time
from sync import syncHandler
#from .exceptions import SuperColliderConnectionError

RESPONSE_TIMEOUT = 0.25

addrMap = {
        0: '/none',
        1: '/notify',
        2: '/status',
        3: '/quit',
        4: '/cmd',
        5: '/d_recv',
        6: '/d_load',
        7: '/d_loadDir',
        8: '/d_freeAll',
        9: '/s_new',
        10: '/n_trace',
        11: '/n_free',
        12: '/n_run',
        13: '/n_cmd',
        14: '/n_map',
        15: '/n_set',
        16: '/n_setn',
        17: '/n_fill',
        18: '/n_before',
        19: '/n_after',
        20: '/u_cmd',
        21: '/g_new',
        22: '/g_head',
        23: '/g_tail',
        24: '/g_freeAll',
        25: '/c_set',
        26: '/c_setn',
        27: '/c_fill',
        28: '/b_alloc',
        29: '/b_allocRead',
        30: '/b_read',
        31: '/b_write',
        32: '/b_free',
        33: '/b_close',
        34: '/b_zero',
        35: '/b_set',
        36: '/b_setn',
        37: '/b_fill',
        38: '/b_gen',
        39: '/dumpOSC',
        40: '/c_get',
        41: '/c_getn',
        42: '/b_get',
        43: '/b_getn',
        44: '/s_get',
        45: '/s_getn',
        46: '/n_query',
        47: '/b_query',
        48: '/n_mapn',
        49: '/s_noid',
        50: '/g_deepFree',
        51: '/clearSched',
        52: '/sync',
        53: '/d_free',
        54: '/b_allocReadChannel',
        55: '/b_readChannel',
        56: '/g_dumpTree',
        57: '/g_queryTree',
        58: '/error',
        59: '/s_newargs',
        60: '/n_mapa',
        61: '/n_mapan',
        62: '/n_order',
        63: '/p_new',
        64: '/version',
}

def counter():
    i = 0
    while True:
        i = i + 1
        yield i


class Server(object):
    """Lightweight (incomplete) wrapper for SC server"""
    def __init__(self):

        #osc4py3 labels
        self.recvID = "sc"
        self.sendID = "bobby"

        self.syncID = counter()
        self.syncIDs = {}

        self.latency = 0.2

        osc_startup()
        #SuperCollider server
        osc_udp_client("127.0.0.1", 57110, self.sendID);

        #Get port of sending socket, and use it to create a receiving server
        recvPort = oscchannel.get_channel(self.sendID).udpsock.getsockname()[1];
        osc_udp_server("127.0.0.1", recvPort, self.recvID)

        osc_method('/synced', self.syncHandler)

    def syncHandler(self, *args):
        for id, ev in self.syncIDs.items():
            if (args[0] == id):
                ev.set()
                self.syncIDs.pop(id)

    def send_msg(self, addr, msg, types=None):
        """Send OSC message immediately"""
        osc_send(oscbuildparse.OSCMessage(addr, types, msg), self.sendID)
        osc_process()

    def bundle_add(self, addr, msg, bundle, types=None):
        """Add message to a bundle"""
        bundle.append(oscbuildparse.OSCMessage(addr, types, msg))

    def send_bundle(self, time, bundle):
        if bundle:
            osc_send(oscbuildparse.OSCBundle(time + self.latency, bundle), self.sendID)
            osc_process()

    def notify(self):
        pass

    async def sync(self, timeout=1):
        id = next(self.syncID)
        self.syncIDs[id] = asyncio.Event()
        msg = oscbuildparse.OSCMessage('/sync', None, [id])
        osc_send(msg, self.sendID)
        osc_process()
        await asyncio.wait_for(self.syncIDs[id].wait(), timeout=timeout)

    async def bootSync(self, timeout=20):
        while True:
            try:
                await self.sync(1)
                break
            except asyncio.TimeoutError:
                print("Waiting for server...")

    def waitForBoot(self, timeout=20):
        asyncio.get_event_loop().run_until_complete(asyncio.wait_for(self.bootSync(), timeout=timeout))
