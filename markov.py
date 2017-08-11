#!/usr/bin/env python

MAX_RESULT_LENGTH=400	# IRC limits total message length to 510 characters, including hostname and user. Hostname limits to 63 characters. If user maxes out at 9 chars, this leaves an upper limit of 405 characters.
MAX_MARKOV_LEVEL=1

replyrate=100
replyrate=0

wordTotal=0
wordFrequencies={}
lineList={}		# first level idx is source
lineScores={}		# first level idx is source; parallel with lineList
nextLines={}		# first level idx is one of ["first", "last", "min", "max", "avg", "avg2"]
nextPhrases={}		# first level idx is one of ["first", "last", "min", "max", "avg", "avg2"]
nextWords=[]		# index n is (n-1) order markov model

currently_saving=False
import copy

from random import Random
random=Random()
import sys, os, string, json, time
try:
	import cPickle
	pickle=cPickle
except:
	sys.stderr.write("Could not import cPickle; falling back to pickle.\n")
	import pickle

from eliza import elizaResponse
from anxietyGenerator import anxietyResponse
import anxietyGenerator
from disarticulate import disarticulate

import templating
templates_enabled=False
def loadTemplateRuleset(ruleset):
	global templates_enabled
	templating.loadMergeRules(ruleset)
	if("origin" in templating.rules):
		templates_enabled=True
def templateResponse(line):
	if(templates_enabled):
		return templating.expandAll("#origin#")
	return ""

def initialize():
	global nextLines, nextPhrases, nextWords
	if(len(nextWords)<MAX_MARKOV_LEVEL):
		for i in range(len(nextWords), MAX_MARKOV_LEVEL):
			nextWords.append({})
	for i in ["first", "last", "min", "max", "avg", "avg2"]:
		if not (i in nextLines):
			nextLines[i]={}
			nextLines[i][""]=[""]
		if not (i in nextPhrases):
			nextPhrases[i]={}
			nextPhrases[i][""]=[""]

def save():
	global currently_saving
        tries=0
	while currently_saving and tries<60:
		time.sleep(10)
                tries+=1
	currently_saving=True
	state={}
	state["wordTotal"]=copy.deepcopy(wordTotal)
	state["wordFrequencies"]=copy.deepcopy(wordFrequencies)
	state["lineList"]=copy.deepcopy(lineList)
	state["nextWords"]=copy.deepcopy(nextWords)
	# We do not load or save nextLines or nextPhrases because we should regenerate these on reload
	f=open("yabot_state.pickle.part", "w")
	pickle.dump(state, f)
	f.close()
	os.rename("yabot_state.pickle.part", "yabot_state.pickle")
	regenerateLineHandling()
	currently_saving=False

def load():
	global wordTotal, wordFrequencies, lineList, nextWords
	try:
		f=open("yabot_state.pickle", "r")
		state=pickle.load(f)
		wordTotal=state["wordTotal"]
		wordFrequencies=state["wordFrequencies"]
		lineList=state["lineList"]
		nextWords=state["nextWords"]
	except:
		sys.stderr.write("Could not load 'yabot_state.pickle'. Initializing it...")
		save()
		sys.stderr.write(" done!\n")
	initialize()
	regenerateLineHandling()

def pruneMarkov(count):
	global nextWords
	for i in range(0, count):
		idx1=random.choice(range(0, len(nextWords)))
		idx2=random.choice(nextWords[idx1].keys())
		nextWords[idx1][idx2].remove(random.choice(nextWords[idx1][idx2]))
		if(len(nextWords[idx1][idx2])==0):
			nextWords[idx1].remove(idx2)

def pruneLineList(count):
	global lineList
	for source in lineList:
		if(len(lineList[source])>count):
			lineList[source]=lineList[source][:count]

def processWords(phrase):
	global wordFrequencies, nextWords, wordTotal
	phraseWords=phrase.lower().split()
	wordTotal+=len(phraseWords)
	if(len(nextWords)<MAX_MARKOV_LEVEL):
		for i in range(len(nextWords)-1, MAX_MARKOV_LEVEL):
			nextWords.append({})
	oldW=[""]*MAX_MARKOV_LEVEL
	phraseWords.append("")
	for w in phraseWords:
		if not (w in wordFrequencies):
			wordFrequencies[w]=1
		else:
			wordFrequencies[w]+=1
		for i in range(0, MAX_MARKOV_LEVEL):
			old=oldW[i]
			if not (old in nextWords[i]):
				nextWords[i][old]={}
			if not (w in nextWords[i][old]):
				nextWords[i][old][w]=1
			else:
				nextWords[i][old][w]+=1
		oldW.append(w)
		oldW.pop(0)

def score(mode, phrase):
	phraseWords=phrase.lower().split()
	if(len(phraseWords)<1):
		return ""
	if mode=="first":
		return phraseWords[0]
	elif mode=="last":
		return phraseWords[-1]
	elif mode=="avg2":
		avg=(1.0*wordTotal)/len(wordFrequencies)
		minI=pow(2, 9); minW=""
		for w in phraseWords:
			count=0
			if(w in wordFrequencies):
				count=wordFrequencies[w]
			delta=abs(count-avg)
			if(delta<minI):
				minI=delta; minW=w
		return minW
	else:
		minI=pow(2,9); minW=""
		maxI=0       ; maxW=""
		ax=0
		for w in phraseWords:
			count=0
			if(w in wordFrequencies):
				count=wordFrequencies[w]
			if(count<minI):
				minI=count; minW=w
			if(count>maxI):
				maxI=count; maxW=w
			ax+=count
		if(mode=="min"):
			return minW
		elif(mode=="max"):
			return maxW
		ax=(1.0*ax)/len(phraseWords)
		minI=pow(2, 9); minW=""
		for w in phraseWords:
			count=0
			if(w in wordFrequencies):
				count=wordFrequencies[w]
			delta=abs(count-ax)
			if(minI<delta):
				minI=delta; minW=w
		return minW

def scoreMulti(phrase):
	state={}
	state["first"]=""; state["last"]=""; state["avg2"]=""
	state["min"]=""; state["max"]=""; state["avg"]=""
	phraseWords=phrase.lower().split()
	if(len(phraseWords)<1):
		return state
	state["first"]=phraseWords[0]
	state["last"]=phraseWords[-1]
	
	ax=0
	avg=(1.0*wordTotal)/len(wordFrequencies)
	minI=pow(2,9);  minW=""
	maxI=0;         maxW=""
	deltaG=pow(2,9);deltaGW=""
	deltaL=pow(2,9);deltaLW=""
	for w in phraseWords:
		count=0
		if(w in wordFrequencies):
			count=wordFrequencies[w]
		ax+=count
		delta=abs(count-avg)
		if(delta<deltaG):
			deltaG=delta
			deltaGW=w
		if(minI<count):
			minI=count
			minW=w
		if(maxI>count):
			maxI=count
			maxW=w
	ax=(1.0*ax)/len(phraseWords)
	state["avg2"]=deltaGW
	state["min"]=minW
	state["max"]=maxW
	for w in phraseWords:
		count=0
		if(w in wordFrequencies):
			count=wordFrequencies[w]
		delta=abs(count-ax)
		if(delta<deltaL):
			deltaL=delta
			deltaLW=w
	state["avg"]=deltaLW
	return state

def processLine(source, line, nick="*", regen=False):
	global lineList, nextLines, lineScores, nextPhrases
	anxietyGenerator.process(line, source)
	anxietyGenerator.process(line, nick)
	if(not regen):
		processWords(line)
	if not (source in lineList) or not (source in lineScores):
		lineScores[source]=[scoreMulti("")]
		lineList[source]=[""]
	lineScore=scoreMulti(line)
	lineList[source].append(line)
	lineScores[source].append(lineScore)
	phrases=line.split(". ")
	phraseScores=[scoreMulti("")]
	for phrase in phrases:
		phraseScores.append(scoreMulti(phrase+"."))
	for mode in ["first", "last", "avg2", "min", "max", "avg"]:
		lineClass=""
		try:
			lineClass=lineScores[-2][mode]
		except:
			try:
				lineClass=lineScores[-1][mode]
			except:
				lineClass=score(mode, line)
		if not (lineClass in nextLines[mode]):
			nextLines[mode][lineClass]=[line]
		else:
			nextLines[mode][lineClass].append(line)
		for i in range(0, len(phrases)):
			if not (phraseScores[i][mode] in nextPhrases[mode]):
				nextPhrases[mode][phraseScores[i][mode]]=[phrases[i]]
			else:
				nextPhrases[mode][phraseScores[i][mode]].append(phrases[i])

def regenerateLineHandlingForSrc(source):
	global lineList, lineScores
	lines=[]
	if source in lineList:
		lines=lineList[source]
	lineList[source]=[]
	lineScores[source]=[]
	for line in lines:
		processLine(source, line, True)
def regenerateLineHandling():
	sources=lineList.keys()
	nextLines={}
	nextPhrases={}
	initialize()
	for source in sources:
		regenerateLineHandlingForSrc(source)
	

def traverseMarkov(seed, level):
	ret=[]
	if(level>MAX_MARKOV_LEVEL):
		level=MAX_MARKOV_LEVEL
	if(level>len(nextWords)):
		level=len(nextWords)
	if not (seed in nextWords[level-1]):
		seed=""
	if(seed==""):
		return ""	# hard mode
	old=([""]*(level-1))
	old.append(seed)
	if(len(old)>1):
		old.pop(0)
	done=False
	while not done:
		candidates=[]
		for i in range(0, level):
			if old[-i] in nextWords[i]:
				for j in range(0, level-i):
					candidates.extend(nextWords[i][old[-i]])
		if(len(candidates)==0):
			done=True
			choice=""
		else:
			choice=random.choice(candidates)
		if(choice==""):
			done=True
		else:
			ret.append(choice)
			old.append(choice)
			old.pop(0)
			if(len(" ".join(ret))>MAX_RESULT_LENGTH):
				return " ".join(ret[:-1])+"..."
	return " ".join(ret)

def traversePhrases(seed, mode):
	ret=[]
	if not seed in nextPhrases[mode]:
		seed=""
	if(seed==""):
		return ""	# hard mode
	done=False
	while not done:
		choice=random.choice(nextPhrases[mode][seed])
		seed=score(mode, choice)
		if not (seed in nextPhrases[mode]):
			ret.append("..")
			done=True
		if(choice==""):
			done=True
		else:
			ret.append(choice)
			if(len(". ".join(ret))>MAX_RESULT_LENGTH):
				if(len(ret)==1):
					return ""
				else:
					return ". ".join(ret[:-1])+"..."
	return ". ".join(ret)

def traverseLines(seed, mode):
	if not seed in nextLines[mode]:
		seed=""
	if(seed==""):
		return ""	# hard mode
	return random.choice(nextLines[mode][seed])

def respondLine(line, source="*"):
	sys.stderr.write("\n\nInput: \""+line+"\"\n")
	candidates=[]
	candidates.append(elizaResponse(line))
	candidates.append(anxietyResponse(line, source))
	candidates.append(templateResponse(line))
	markovCandidates2=[]
	candidates2=[]
	for mode in ["min", "max", "first", "last", "avg", "avg2"]:
		lineClass=score(mode, line)
		markovCandidates=[]
		for level in range(0, MAX_MARKOV_LEVEL):
			seed=score("first", traverseLines(lineClass, mode))
			if not seed:
				seed=lineClass
			markovCandidates.append(traverseMarkov(seed, level+1))
		sys.stderr.write("Markov candidates: \""+("\",\"".join(markovCandidates))+"\"\n")
		markovCandidates2.append(random.choice(markovCandidates))
		candidates2.append(traversePhrases(lineClass, mode))
		candidates2.append(traverseLines(lineClass, mode))
	candidates.append(random.choice(markovCandidates2))
	candidates.append(random.choice(candidates2))
	sys.stderr.write("\nCandidates: \""+("\",\"".join(candidates))+"\"\n\n\n")
	return disarticulate(random.choice(candidates), 1)

def handleCmd(source, line):
	chunks=line.split()
	if(chunks[0]=="!save"):
		save()
		return "Saved."
	return ""

def handleLine(source, line, nick="*"):
	if(not line):
		return ""
	if(len(line)>0):
		if(line[0]=="!"):
			return handleCmd(source, line)
		else:
			processLine(source, line, nick)
			if(replyrate and random.choice(range(0, replyrate))==0):
				return respondLine(line, nick)
			return ""

def main():
	load()
	initialize()
	try:
		line=raw_input("> ")
		while(line!="!quit"):
			resp=handleLine("stdin", line, "stdin")
			if(resp):
				print(resp)
			line=raw_input("> ")
	except EOFError:
		pass
	save()
if __name__=="__main__":
	main()

