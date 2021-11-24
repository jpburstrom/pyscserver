#!/usr/bin/env python

import time
import subprocess
import json
#from pythonosc import udp_client
from osc4py3.as_eventloop import *
from osc4py3 import oscbuildparse, oscchannel

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

def syncHandler(*args):
    print(args)
    print("synced")

class Score:
    def __init__(self, path, server="sc"):
        #TODO error handling
        with open(path) as file:
            self.score = json.load(file)
        self.bundle = []
        self.receiver = "sc" #osc4py3 handle
        self.curTime = 0 # Time relative to score start
        self.scoreActions = {
            '/d_recv': self.msg_d_recv
        }

    def send_msg(self, addr, msg, types=None):
        """Send OSC message immediately"""
        osc_send(oscbuildparse.OSCMessage(addr, types, msg), self.receiver)
        osc_process()

    def bundle_add(self, addr, msg):
        self.bundle.append(oscbuildparse.OSCMessage(addr, None, msg))

    def msg_default(self, addr, args):
        """Format and send message, default method"""
        self.bundle_add(addr, args)

    def msg_d_recv(self, addr, args):
        """Format and send /d_recv message"""
        try:
            completionMsg = oscbuildparse.encode_packet(oscbuildparse.OSCMessage(args[1][0], None, args[1][1:]))
        except TypeError:
            completionMsg = None
        self.send_msg(addr, [bytes([x + 128 for x in args[0]]), completionMsg])

    def play(self):
        self.oscStartTime = oscbuildparse.unixtime2timetag(time.time())
        for item in self.score:
            self.process_row(item)
            self.send_bundle()

    def process_row(self, item):
        """Process a single score row."""

        #self.maybe_send_bundle(item[0])
        self.curTime = item[0]
        message = item[1] # message format: [addr, arg1, arg2..]
        try:
            addr = addrMap[message[0]]
        except KeyError:
            addr = message[0]
        self.scoreActions.get(addr, self.msg_default)(addr, message[1:])

    def maybe_send_bundle(self, time):
        """Send bundle if provided time is more than current time."""

        if time > self.curTime:
            self.send_bundle()

    def send_bundle(self):
        if self.bundle:
            osc_send(oscbuildparse.OSCBundle(self.oscStartTime + self.curTime, self.bundle), self.receiver)
            osc_process()
            self.bundle = []




if __name__ == '__main__':

    osc_startup()
    #SuperCollider server
    osc_udp_client("127.0.0.1", 57110, "sc");

    #Get port of sending socket, and use it to create a receiving server
    recvPort = oscchannel.get_channel("sc").udpsock.getsockname()[1];
    osc_udp_server("127.0.0.1", recvPort, "this")

    #Then we can use sync messages - this is a test
    #TODO implement sync in Score class
    osc_method("/synced", syncHandler)
    msg = oscbuildparse.OSCMessage('/sync', None, [1])


    scsynth = subprocess.Popen([ "/Users/johannes/bin/scsynth", "-u", "57110", "-a", "1024", "-i", "2", "-o", "2", "-R", "0", "-C", "1", "-l", "2", "-s", "1.26" ])
    #TODO Wait for boot
    #Send /notify repeatedly, wait for answer
    #Send init tree
    #play score

    score = Score("test.json")
    score.play()

    finished = False
    while not finished:
        osc_process()
        if scsynth.poll() is not None:
            finished = True
        time.sleep(0.05)

    osc_terminate()

