#!/usr/bin/env python
"""
    consume_process.py -- Example approach to streaming subprocess output

    Example executes "find /" which easily congests incorrect handling

    Change the 'cmd' to e.g. "find /root" to see what happens in case of error
"""
from __future__ import print_function
from subprocess import Popen, PIPE
from collections import deque
import select

def consume(process):
    """Produces a (stdout, stderr) generator from the given process"""

    while process.poll() is None:   # While executing, stream output
        rdrs, _, _ = select.select([process.stdout, process.stderr], [], [])

        for rdr in rdrs:
            if rdr == process.stdout:
                yield (rdr.read(1), None)
            elif rdr == process.stderr:
                yield (None, rdr.read(1))

    yield process.communicate()     # When process is done, grab the remainder

def main():
    """Example use of streaming output from subprocess."""

    cmd = ["find", "/"]
    process = Popen(cmd, stdout=PIPE, stderr=PIPE)

    errors = deque()

    for stdout, stderr in consume(process):
        if stdout:
            pass
            #print(stdout, end='')

        if stderr:
            errors.append(stderr)

    if errors:
        print("\nerrors(%s)" % ("".join(errors)).strip())

if __name__ == "__main__":
    main()
