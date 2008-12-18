#!/usr/bin/env python

import os
import sys
import re
from select import select
from subprocess import Popen, PIPE

import time

# XPipe prototype - might rewrite in C later to reduce memory overhead and dependencies
# Making this a binary will also allow us to use #! in pipe files, and use them as programs themselves, which would be neat

# TODO: special STDIN and STDOUT commands, so we can handle them

def debug_print(x):
	pass

class GraphNodeStream:
	def __init__(self, node, stream, name):	
		self.node = node
		self.stream = stream
		self.name = name
	
	def fileno(self):
		return self.stream.fileno()
	
	def is_live(self):
		return self.stream is not None and not self.stream.closed
	
	def __repr__(self):
		return self.node.__repr__() + "." + self.name

class GraphNode:
	def __init__(self, name, command):
		self.name = name
		self.command = command
		self.process = None
		self.stdin = None
		self.stdout = None
		self.outputs = []
	
	def execute(self):
		if self.command is not None:
			self.process = Popen(self.command, shell=True, stdin=PIPE, stdout=PIPE, stderr=None)
			self.stdin = GraphNodeStream(self, self.process.stdin, 'stdin')
			self.stdout = GraphNodeStream(self, self.process.stdout, 'stdout')
	
	def is_live(self):
		if self.process is not None:
			self.process.poll()
		return self.command is None or (self.process is not None and self.process.returncode is None)
	
	def is_readable(self):
		return self.stdout.is_live()
	
	def is_writable(self):
		return self.stdin.is_live()
	
	def __repr__(self):
		if self.command is None:
			return "(" + self.name + ")"
		return "(" + self.name + ": " + self.command + ")"
	

### Read input files

# map of command names to commands (later, becomes a map of command names to GraphNode instances)
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

# create special stdin and stdout commands
fake_stdout = GraphNode('STDOUT', None)
fake_stdout.stdin  = GraphNodeStream(fake_stdout, sys.stdout, 'stdin')
fake_stdout.stdout = GraphNodeStream(fake_stdout, None, 'stdout')
cmds['STDOUT'] = fake_stdout

fake_stdin = GraphNode('STDIN', None)
fake_stdin.stdin  = GraphNodeStream(fake_stdin, None, 'stdin')
fake_stdin.stdout = GraphNodeStream(fake_stdin, sys.stdin, 'stdout')
cmds['STDIN'] = fake_stdin

# second pass - fill in outputs with GraphNode objects
for edge in graph:
	for cmd in edge[0], edge[1]:
		if not cmd in cmds:
			print "Invalid edge: Reference to nonexistent command " + cmd
			sys.exit(1)
	cmds[edge[0]].outputs.append(cmds[edge[1]])

#print cmds

### Process pipeline data in a loop

# execute all commands
for cmd in cmds:
	cmds[cmd].execute()

def cleanup_process(cmd):
	for out in cmds[cmd].outputs:
		if out is not fake_stdout:
			out.stdin.stream.close()
	
	for x in cmds:
		if cmds[cmd] in cmds[x].outputs:
			cmds[x].outputs.remove(cmds[cmd])
	
	del cmds[cmd]

while len(cmds) > 2: # 2, because std[in,out] will always be in there # FIXME: this is kinda gross
	r = [ cmds[x].stdout for x in cmds if cmds[x].is_readable() ] # read from stdout streams
	w = [ cmds[x].stdin for x in cmds if cmds[x].is_writable() ]  # write to stdin streams
	x = r + w                                                     # dunno what should go in here :(
	
	r, w, x = select(r, w, x)
	
	debug_print("SELECTED: " + str(r) + str(w) + str(x))
	
	for readable in r:
		debug_print("trying " + str(readable))
		can_read = True
		for out in readable.node.outputs:
			debug_print("   is " + str(out) + " writable?")
			if out.stdin not in w:
				debug_print(str(out) + " is not writable, skipping " + str(readable))
				can_read = False
		
		if can_read:
			debug_print("   can read!")
			data = readable.stream.read(65536)
			
			# FIXME: possible race condition if the process writes more data and then dies right here
			
			if data == "" and (not readable.node.is_live()):
				cleanup_process(readable.node.name)
				continue
			
			debug_print("   read data from " + str(readable.node) + ": " + data)
			for out in readable.node.outputs:
				out.stdin.stream.write(data)
				debug_print("   wrote data to " + str(out))
	
	
	#time.sleep(1)
	
