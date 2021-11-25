#!/usr/bin/env python

import time
import subprocess
import json
import asyncio
#from pythonosc import udp_client
from osc4py3.as_eventloop import *
from osc4py3 import oscbuildparse, oscchannel

from server import Server, addrMap
from serverprocess import ServerProcess

osc_poll_time = 0.1

class Score:
    def __init__(self, path):
        #TODO error handling
        with open(path) as file:
            self.score = json.load(file)
        self.bundle = []
        self.curTime = 0 # Time relative to score start
        self.scoreActions = {
            '/d_recv': self.msg_d_completion,
            '/d_load': self.msg_d_completion,
            '/d_loadDir': self.msg_d_completion,
            'syncFlag': self.msg_sync,
            '/sync': self.msg_sync
        }
        #This is set in the play method
        self._server = None

    def msg_sync(self, addr, args):
        """Process"""
        self.send_bundle() #Send and clear any stray messages
        #Block until complete
        asyncio.get_event_loop().run_until_complete(self._server.sync()) #block further processing

    def msg_default(self, addr, args):
        """Format and send message, default method"""
        self.bundle_add(addr, args)

    def msg_d_completion(self, addr, args):
        """Format and send /d_* message with completion function"""
        try:
            c_addr = self.int_to_addr(args[1][0]) # addr of completion message
            completionMsg = oscbuildparse.encode_packet(oscbuildparse.OSCMessage(c_addr, None, args[1][1:]))
        except TypeError:
            completionMsg = None
        self._server.send_msg(addr, [bytes([(x + 256) % 256 for x in args[0]]), completionMsg])

    def play(self, server):
        self._server = server
        self.oscStartTime = oscbuildparse.unixtime2timetag(time.time())
        for item in self.score:
            self.process_row(item)
            self.send_bundle()

    def int_to_addr(self, addr):
        try:
            addr = addrMap[addr]
        except KeyError:
            pass
        return addr

    def process_row(self, item):
        """Process a single score row."""

        self.curTime = item[0]
        for message in item[1:]:
            addr = self.int_to_addr(message[0])
            self.scoreActions.get(addr, self.msg_default)(addr, message[1:])

    def bundle_add(self, addr, msg):
        """Add message to current bundle"""
        self._server.bundle_add(addr, msg, self.bundle)

    def send_bundle(self):
        if self.bundle:
            self._server.send_bundle(self.oscStartTime + self.curTime, self.bundle)
        self.bundle.clear()

async def poll():
    while 1:
        osc_process()
        await asyncio.sleep(osc_poll_time)

async def stop_loop():
    asyncio.get_event_loop().stop()

if __name__ == '__main__':

    subprocess.run(["killall", "scsynth"])

    loop = asyncio.get_event_loop()
    scsynth = ServerProcess(blockSize=16, executable="/Users/johannes/bin/scsynth")
    osctask = loop.create_task(poll())
    servertask = loop.create_task(scsynth.start_async())
    server = Server()
    server.waitForBoot()
    print("Server booted!")
    server.send_msg('/g_new', [1])
    server.send_msg('/g_dumpTree', [0])
    score = Score("test.json")
    score.play(server)

    #Attach to scsynth and
    loop.run_until_complete(servertask)

    loop.run_until_complete(stop_loop())
    osc_terminate()
