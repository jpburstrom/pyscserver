#!/usr/bin/env python3

import asyncio
import platform
import sys

IS_BELA = platform.release().find('xenomai') != -1

class ServerProcess(object):
    """Wrapper for the scsynth process"""

    def __init__(self, **kwargs):
        """Init class, set options"""
        self.options = {
            'executable': '/usr/bin/scsynth',
            'blockSize': 16,
            'memSize': 262144,
        }

        self.options.update(kwargs)

    def _getCmd(self):
        args = "-u 57110 -a 1032 -i 4 -o 8 -B 0.0.0.0 -R 0 -C 1 -l 2 "
        if IS_BELA:
            args += "-X 0 -Y 0 -A 1 -x 0 -y 0 -g 0 -T 1 -E 0 -J 2 -K 2 -G 16 -Q 0 "
        args += "-z {blockSize:d} -m {memSize:d}".format(**self.options)
        args = args.split(" ")
        args.insert(0, self.options['executable'])
        return args


    async def _read_stream(self, stream, cb):
        while True:
            line = await stream.readline()
            if line:
                cb(line)
            else:
                break

    def _print_stdout(self, line):
        sys.stdout.write(line.decode("utf-8"))

    def _print_stderr(self, line):
        sys.stderr.write("ERR: %s" % line.decode("utf-8"))

    async def start_async(self):
        process = await asyncio.create_subprocess_exec(*self._getCmd(),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)

        await asyncio.wait([
            self._read_stream(process.stdout, self._print_stdout),
            self._read_stream(process.stderr, self._print_stderr)
        ])
        return await process.wait()

    def start(self):
        loop = asyncio.get_event_loop()
        rc = loop.run_until_complete(self.start_async())
        loop.close()
        return rc

if __name__ == '__main__':
    p = ServerProcess(blockSize = 32, executable = "/Users/johannes/bin/scsynth")
    print(p.start_async())
