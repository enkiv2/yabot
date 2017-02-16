#!/usr/bin/env python

import sys

global rules, random, grammar

import re
import json
from random import Random
random=Random()

use_tracery=False

try:
	import tracery
	from tracery.modifiers import base_english
	use_tracery=True
except:
	use_tracery=False
grammar={}
rules={}

tag=re.compile("#[a-zA-Z0-9]*#")

def expandTag(match):
	tname=match.string[match.start()+1:match.end()-1]
	if(tname in rules):
		rule=rules[tname]
		return random.choice(rule)
	return tname

def performExpansion(line):
	return tag.sub(expandTag, line)

def expandAll(line, ttl=999):
	global rules, grammar
	if(use_tracery):
		return grammar.flatten(line)
	while(ttl>0 and len(line)<140 and None!=tag.search(line)):
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
		opt2=opt
		opt2.extend(rules[name])
		rules[name]=opt2
	else:
		rules[name]=opt

def loadMergeRules(fname):
	global rules, grammar
	with open(fname, "r") as f:
		rules2=json.load(f)
		for rule in rules2:
			mergeRule(rule, rules2[rule])
	if(use_tracery):
		grammar=tracery.Grammar(rules)
		grammar.add_modifiers(base_english)

def loadRules(fname):
	global rules, grammar
	with open(fname, "r") as f:
		rules=json.load(f)
	if(use_tracery):
		grammar=tracery.Grammar(rules)
		grammar.add_modifiers(base_english)


def main():
	loadRules(sys.argv[1])
	print(expandAll("#origin#"))

if __name__=="__main__":
	main()

