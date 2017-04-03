#!/usr/bin/env python
from __future__ import print_function
from subprocess import Popen, PIPE
from collections import deque
import curses.ascii
import curses
import select
import shutil
import shlex
import time
import sys

KEY_CTRL_D = 4
KEY_BS = 263
KEY_RESIZE = 410

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

class Screen(object):

    def __init__(self):
        self.scr = curses.initscr()

        self.height, self.width = self.scr.getmaxyx()
        self.status = curses.newwin(1, self.width, self.height - 1, 0)
        self.prompt = curses.newwin(1, self.width, self.height - 2, 0)
        self.prompt.keypad(1)
        self.output = curses.newwin(self.height - 2, self.width, 0, 0)

        curses.noecho()
        curses.cbreak()
        curses.start_color()
        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)

        self.status_msg = ""

        self.hist = deque()
        self.ibuf = []
        self.output_buf = []

        self.cmds = {
	    "clear": self.bi_clear
	}

    def __del__(self):
        curses.echo()
        curses.nocbreak()
        curses.endwin()

    def bi_clear(self, cmd):
	self.output_buf = []
        self.output.clear()
	
	height, width = self.output.getmaxyx()
	empty_line = " " * width

	for line_nr in xrange(0, height - 1):
	    self.output.addstr(line_nr, 0, empty_line)

	self.output.refresh()

    def status_set(self, msg):

        self.status_msg = str(msg)

    def status_err(self, msg):

        self.status_set(str(msg))
        self.status_draw()

    def output_add(self, msg):

        self.output_buf.append(msg)

    def output_draw(self):

        self.output.clear()
        height, width = self.output.getmaxyx()

        empty_line = " " * width

        for count, line in enumerate(self.output_buf[::-1][:height]):

            for foo in line.split('\n'):
                self.output.addstr(height - 1 - count, 0, foo)

        self.output.refresh()

    def status_draw(self):

        status_str = ""

        if self.status_msg:
            status_str = str(self.status_msg)

        self.status.clear()
        self.status.attron(curses.color_pair(3))
        self.status.addstr(0, 0, status_str)
        self.status.addstr(0, len(status_str), " " * (self.width -
            len(status_str) - 1))
        self.status.attroff(curses.color_pair(3))
        self.status.refresh()

    def prompt_draw(self):

        try:
            user_input = "".join([chr(x) for x in self.ibuf])
            ostr = "cmd: %s" % user_input

            self.prompt.clear()
            self.prompt.attron(curses.color_pair(1))
            self.prompt.addstr(0, 0, ostr)
            self.prompt.addstr(0, len(ostr), " " * (self.width - len(ostr) - 1))
            self.prompt.attroff(curses.color_pair(3))
            self.prompt.move(0, len(ostr))
            self.prompt.refresh()
        except Exception as e:
            self.status_set(str(e))
            self.status_draw()

    def clear(self, clear_all=False):
        self.height, self.width = self.scr.getmaxyx()
        self.scr.clear()

        if clear_all:
            self.prompt.clear()
            self.status.clear()
            self.output.clear()

    def refresh(self, refresh_all=False):
        self.scr.refresh()

        if refresh_all:
            self.prompt.refresh()
            self.status.refresh()
            self.output.refresh()

    def completion(self, key):
        self.status_set("Completion time!")
        self.status_draw()

    def execute_shell(self, cmd):

	try:
        	prcs = Popen(cmd, stdout=PIPE, stderr=PIPE)
	except:
		return

        out = []
        err = []
        for stdout, stderr in consume(prcs):

            if stdout:
		if len(stdout) > 1:
                    for count, line in enumerate((x for x in stdout.split('\n') if x)):
			if not count:
			    line = "".join(out + [line])
			    out = []
			self.output_add(line)
		elif stdout == '\n':
                    self.output_add("".join(out))
                    out = []
                    self.output_draw()
                else:
                    out.append(stdout)

            #if stderr:
            #    if stderr == '\n':
            #        self.output_add("".join(err))
            #        err = []
            #        self.output_draw()
            #    else:
            #        err.append(stderr)

        if out:
            self.output_add("".join(out))
            out = []

        if err:
            self.output_add("".join(err))
            err = []

        self.output_draw()

    def execute(self, key):

        if not self.ibuf:
            self.status_set("Exec: NOOP")
            self.status_draw()
            return

        cmd = "".join([chr(x) for x in self.ibuf])

        cmd_tokens = shlex.split(cmd)
        cmd_head = cmd_tokens[0]

        self.ibuf = []  # Clear the input buffer
        self.hist.append(cmd)

        self.status_set("Exec: cmd(%s)" % cmd)
        self.status_draw()

        if cmd_head in self.cmds:
	    try:
            	self.cmds[cmd_head](cmd_tokens)
            except:
		with open("/tmp/chess.log", "a") as err:
		    err.write(str(sys.exc_info()))
	else:
            self.execute_shell(cmd_tokens)

    def resize(self):

        if curses.is_term_resized(self.height, self.width):
            self.height, self.width = self.scr.getmaxyx()

            curses.resizeterm(self.height, self.width)
            self.clear(True)

            self.output.resize(self.height - 2, self.width)
            self.status.resize(1, self.width)
            self.prompt.resize(1, self.width)

            self.status.mvwin(self.height - 1, 0)
            self.prompt.mvwin(self.height - 2, 0)
            self.output.mvwin(0, 0)
            self.refresh(True)

    def loop(self):
        do_run = True

        while do_run:
            self.clear()
            self.status_draw()
            self.prompt_draw()

            key = self.prompt.getch()

            if key is curses.ascii.TAB:
                self.completion(key)
            elif key is curses.ascii.LF:
                self.execute(key)
            elif key is curses.ascii.CR:
                self.execute(key)
            elif key is KEY_CTRL_D:
                self.status_set("Exiting...")
                do_run = False
            elif key in [curses.ascii.BS, KEY_BS]:
                if len(self.ibuf) > 0:
                    self.ibuf.pop()
            elif key >=0 and key <= 255:
                self.ibuf.append(key)
            elif key in [curses.KEY_RESIZE]:
                self.resize()
            else:
                self.status_set("Unknown input key(%s)" % str(key))
                pass

def main():
    try:
        scr = Screen()
        scr.loop()
    except:
        with open("/tmp/chess.err", "w") as err:
            err.write(str(sys.exc_info()))

if __name__ == "__main__":
    main()
