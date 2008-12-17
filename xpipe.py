#!/usr/bin/env python

import os
import sys
import re
from select import select
from subprocess import Popen, PIPE

# XPipe prototype - might rewrite in C later to reduce memory overhead and dependencies

class GraphNode:
	def __init__(self, name, command, process):
		self.name = name
		self.command = command
		self.process = None
		self.children = []
	
	def execute(self):
		self.process = Popen(self.command, shell=True, stdin=PIPE, stdout=PIPE, stderr=None)
	
	

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
		proc = Popen(command, shell=True, stdin=PIPE, stdout=PIPE, stderr=None)
		cmds[name] = (proc.stdin, proc.stdout)
	
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


# map of name to (stdin, stdout) tuples
cmds = parse_commands(sys.argv[1])

# list of (name, compiled pattern, name) tuples
graph = parse_graph(sys.argv[2], cmds)



while len(cmds) < 0:
	r = [ cmds[x][1] for x in cmds] # read from stdout streams
	w = [ cmds[x][0] for x in cmds] # write to stdin streams
	x = r + w # dunno what should go in here :(
	
	r, w, x = select(r, w, x)
	
	