#!/usr/bin/env python

import sys

global rules, random

import re
import json
from random import Random
random=Random()

rules={}

tag=re.compile("#[^# ]*#")

def expandTag(match):
	tname=match.string[match.pos+1:match.end()-1]
	if(tname in rules):
		rule=rules[tname]
		return random.choice(rule)
	return tname

def performExpansion(line):
	return tag.sub(expandTag, line)

def expandAll(line, ttl=100):
	while(None!=tag.search(line) and ttl>0):
		ttl-=1
		line=performExpansion(line)
		#print("Iter: "+line)
	return line

def addRule(name, opt):
	global rules
	rules[name]=opt

def mergeRule(name, opt):
	global rules
	if(name in rules):
		opt.extend(rules[name])
		rules[name]=opt
	else:
		rules[name]=opt

def loadMergeRules(fname):
	global rules
	with open(fname, "r") as f:
		rules2=json.load(f)
		for rule in rules2:
			mergeRule(rule, rules2[rule])

def loadRules(fname):
	global rules
	with open(fname, "r") as f:
		rules=json.load(f)


def main():
	loadRules(sys.argv[1])
	print(expandAll("#origin#"))

if __name__=="__main__":
	main()

