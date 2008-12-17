#!/usr/bin/env python

import os
import sys
import re
from select import select
from subprocess import Popen, PIPE

# XPipe prototype - might rewrite in C later to reduce memory overhead and dependencies

class GraphNodeStream:
	def __init__(self, node, stream):	
		self.node = node
		self.stream = stream
	
	def fileno(self):
		return self.stream.fileno()

class GraphNode:
	def __init__(self, name, command):
		self.name = name
		self.command = command
		self.process = None
		self.stdin = None
		self.stdout = None
		self.outputs = []
	
	def execute(self):
		self.process = Popen(self.command, shell=True, stdin=PIPE, stdout=PIPE, stderr=None)
		self.stdin = GraphNodeStream(self, self.process.stdin)
		self.stdout = GraphNodeStream(self, self.process.stdout)
	
	def __repr__(self):
		return "(" + self.name + ": " + ",".join([ x.name for x in self.outputs ]) + ")"
	
	
rm = """
def parse_commands(f):
	cmds_file = open(f)
	line_pattern = re.compile(r"(\w+)\s+(.+)")
	lineno = 0
	cmds = {}
	for line in cmds_file:
		lineno += 1
		
		# skip blank lines
		if line.strip() == "":
			continue
		
		# parse lines w/ a regex
		m = line_pattern.match(line)
		if not m:
			print "Error at line %d of command file: %s" % (lineno, line)
			continue
		name, command = m.groups()
		cmds[name] = command
	
	return cmds

def parse_graph(f, cmds):
	graph_file = open(sys.argv[2])
	line_pattern = re.compile(r"(\w+)\s+/(.*)/\s+(\w+)")
	lineno = 0
	graph = []
	for line in graph_file:
		lineno += 1
		
		# skip blank lines
		if line.strip() == "":
			continue
		
		# parse lines w/ a regex
		m = line_pattern.match(line)
		if not m:
			print "Error at line %d of graph file: %s" % (lineno, line)
			continue
		cmd1, regex, cmd2 = m.groups()
		graph.append((cmd1, re.compile(regex), cmd2))
		
		for cmd in cmd1, cmd2:
			if not cmd in cmds:
				print "Error at line %d of graph file: nonexistent command %s" % (lineno, cmd)
		
	return graph
"""

### Read input files

# map of command names to commands
cmds = {}

# list of (name, name) tuples
graph = []

f = open(sys.argv[1])
cmd_pattern = re.compile(r"CMD\s+(\w+)\s+(.*)\s*")
edge_pattern = re.compile(r"EDGE\s+(\w+)\s+(\w+)\s*")
comment_pattern = re.compile(r"\s*#.*")
lineno = 0
for line in f:
	lineno += 1
	
	# skip blank lines
	if line.strip() == "":
		continue
	
	m = cmd_pattern.match(line)
	if m:
		name, command = m.groups()
		cmds[name] = command
		continue
	
	m = edge_pattern.match(line)
	if m:
		src, sink = m.groups()
		graph.append((src, sink))
		continue
	
	m = comment_pattern.match(line)
	if m:
		continue
	
	# if we get here, no patterns matched
	print "Error on line %d: Invalid line" % lineno
	sys.exit(1)


### Construct graph structure

# first pass - construct GraphNode objects
for cmd in cmds:
	cmds[cmd] = GraphNode(cmd, cmds[cmd])

# second pass - fill in outputs with GraphNode objects
for edge in graph:
	for cmd in edge[0], edge[1]:
		if not cmd in cmds:
			print "Invalid edge: Reference to nonexistent command " + cmd
			sys.exit(1)
	cmds[edge[0]].outputs.append(cmds[edge[1]])

print cmds

### Process pipeline data in a loop
rm = """
while len(cmds) < 0:
	r = [ cmds[x][1] for x in cmds] # read from stdout streams
	w = [ cmds[x][0] for x in cmds] # write to stdin streams
	x = r + w # dunno what should go in here :(
	
	r, w, x = select(r, w, x)
	
"""