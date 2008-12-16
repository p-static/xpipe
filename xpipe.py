#!/usr/bin/env python

import os
import sys
import re
from subprocess import Popen, PIPE

# XPipe prototype - might rewrite in C later to reduce memory overhead and dependencies

# list of (name, compiled pattern, name) tuples
graph = []

# map of name to (stdin, stdout) tuples
cmds = {}

graph_file = open(sys.argv[1])
line_pattern = re.compile(r"(\w+)\s/(.*)/\s(\w+)")
lineno = 0
for line in graph_file:
	lineno += 1
	
	# skip blank lines
	if line.strip() == "":
		continue
	
	# parse lines w/ a regex
	m = line_pattern.match(line)
	if not m:
		print "Error at line %d: %s" % (lineno, line)
		continue
	cmd1, regex, cmd2 = m.groups()
	graph.append((cmd1, re.compile(regex), cmd2))
	
	for cmd in cmd1, cmd2:
		if not cmd in cmds:
			command = os.environ['CMD_' + cmd]
			proc = Popen(command, shell=True, stdin=PIPE, stdout=PIPE, stderr=None)
			cmds[cmd] = (proc.stdin, proc.stdout)


print graph
print cmds