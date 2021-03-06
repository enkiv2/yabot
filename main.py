#!/usr/bin/env python

import markov
import eliza
import ircbot

import time, sys, os
import threading

from random import Random
random=Random()

TAG_FREQUENCY=20
templates=[]

class YaBot(ircbot.SingleServerIRCBot):
	def __init__(self, server_list, nickname, realname, owners, channels, password=""):
		ircbot.SingleServerIRCBot.__init__(self, server_list, nickname, realname)
		self.owners=owners
		self.trolls=[]
		self.channelList=channels
		self.password=password
		self.logfilename="yabot.log"
		self.logfile=open(self.logfilename, "a")
                self.starttime=time.time()
		self.periodicReconnect()
	def on_pubmsg(self, c, e):
		self.processAndReply(c, e)
	def on_privmsg(self, c, e):	
		self.processAndReply(c, e, True)
	def logAndPrint(self, line):
		print(line)
		self.logfile.write(line+"\n")
		if(random.choice(range(0, 200))==0):
			self.autosave()
	def periodicReconnectHelper(self):
		time.sleep(100)
		while True:
			self.autosave()
			time.sleep(60*60*12)
			self.jump_server()
        def periodicReconnect(self):
		t=threading.Thread(target=self.periodicReconnectHelper)
		t.start()
	def save_helper(self):
		print("Autosaving markov...")
		markov.save()
		print("Regenerating line metrics...")
		markov.regenerateLineHandling()
		print("Saved")
	def autosave(self):
		print("Autosaving log...")
		self.logfile.flush()
		t=threading.Thread(target=self.save_helper)
		t.start()
	def processAndReply(self, c, e, privmsg=False):
		line=e.arguments()[0]
		source=e.source()
		nick=source.split("!")[0]
		chan=e.target()
		if(chan[0]!="#"):
			chan=nick	# privmsg
		self.logAndPrint("<-\t"+chan+"\t<"+nick+"> "+line)
		if(nick in self.owners and line[0]=="!"):
			self.handleCmd(chan, nick, line)
		else:
			resp=""
			procLine=line
			try:
				if(line.find(self._nickname)==0 and len(line.split())>1):
					procLine=" ".join(line.split()[1:])
				markov.processLine(chan, procLine, nick=nick)
				if(markov.replyrate and random.choice(range(0, markov.replyrate))==0):
					resp=markov.respondLine(procLine, source=nick)
				if(not resp):
					if(line.find(self._nickname)>=0 or privmsg or nick in self.trolls):
						resp=markov.respondLine(procLine, source=nick)
						if(not resp):
							resp=eliza.elizaResponse(procLine)
				else:
					if(random.choice(range(1, 100))==0 or nick in self.trolls):
						markov.processLine(chan, eliza.elizaResponse(line))
			except:
				print("Error in handleLine")
				print(sys.exc_info())
			if(resp and resp!=procLine):
				if not privmsg:
					if(random.choice(range(0, TAG_FREQUENCY))==0 or nick in self.trolls):
						resp=nick+": "+resp
				self.say(chan, resp)
	def handleCmd(self, c, nick, line):
		global TAG_FREQUENCY
		if(c[0]!="#"):
			c=nick
		args=line.split()
		if(args[0]=="!quit"):
			self.say(c, "Saving...")
			self.autosave()
			time.sleep(1)
			while markov.currently_saving:
				time.sleep(1)
			self.say(c, "Saved!\nByebye!")
			self.logfile.close()
			if(len(args)>1):
				self.die(args[1])
			else:
				self.die()
			os.exit(0)
		elif (args[0]=="!save" and len(args)==1):
			self.say(c, "Saving...")
			self.autosave()
		elif (args[0]=="!load"):
			self.say(c, "Loading...")
			markov.load()
			self.say(c, "Loaded!")
		elif (args[0]=="!regenLines"):
			markov.regenerateLineHandling()
		elif (args[0]=="!replyrate"):
			if(len(args)==1):
				self.say(c, "Reply rate is set to "+str(markov.replyrate))
			else:
				try:
					markov.replyrate=int(args[1])
					self.say(c, "I will now reply at most 1/"+args[1]+" of the time.")
				except:
					self.say(c, "Usage: !replyrate <n>\nValue n must be a positive integer & replies will max out at 1/n")
		elif (args[0]=="!tagfrequency"):
			if(len(args)==1):
				self.say(c, "Tag frequency is set to "+str(TAG_FREQUENCY))
			else:
				try:
					TAG_FREQUENCY=int(args[1])
					self.say(c, "I will now use nicks in replies at most 1/"+args[1]+" of the time.")
				except:
					self.say(c, "Usage: !tagfrequency <n>\nValue n must be a positive integer & replies will max out at 1/n")
		elif (args[0]=="!part"):
			try:
				if(args[1] in self.channelList):
					self.channelList.remove(args[1])
					self.connection.part(args[1])
			except:
				self.say(c, "Usage: !part #channel")
		elif (args[0]=="!join"):
			try:
				self.channelList.append(args[1])
				self.connection.join(args[1])
			except:
				self.say(c, "Usage: !join #channel")
		elif (args[0]=="!rmowner"):
			try:
				if(args[1] in self.owners):
					self.owners.remove(args[1])
					self.say(c, "Owner "+args[1]+" removed.")
				else:
					self.say(c, "User "+args[1]+" is not an owner.")
			except:
				self.say(c, "Usage: !rmowner nick")
		elif (args[0]=="!addowner"):
			try:
				self.owners.append(args[1])
				self.say(c, "User "+args[1]+" added to owners list.")
			except:
				self.say(c, "Usage: !addowner nick")
		elif (args[0]=="!rmtroll"):
			try:
				if(args[1] in self.trolls):
					self.trolls.remove(args[1])
					self.say(c, "Troll "+args[1]+" removed.")
				else:
					self.say(c, "User "+args[1]+" is not an troll.")
			except:
				self.say(c, "Usage: !rmtroll nick")
		elif (args[0]=="!addtroll"):
			try:
				self.trolls.append(args[1])
				self.say(c, "User "+args[1]+" added to trolls list.")
			except:
				self.say(c, "Usage: !addtroll nick")
		elif (args[0]=="!rmtemplate"):
			try:
				if(args[1] in templates):
					templates.remove(args[1])
					self.say(c, "Template "+args[1]+" removed.")
				else:
					self.say(c, "Filename "+args[1]+" is not in template list.")
			except:
				self.say(c, "Usage: !rmtemplate filename")
		elif (args[0]=="!addtemplate"):
			try:
				templates.append(args[1])
				markov.loadTemplateRuleset(args[1])
				self.say(c, "Filename "+args[1]+" added to templates list.")
			except:
				self.say(c, "Usage: !addtemplate filename")
		elif(args[0]=="!rejoin"):
			self.rejoin()
		elif(args[0]=="!nick"):
			try:
				self.connection.nick(args[1])
				self._nickname=args[1]
			except:
				self.say(c, "Usage: !nick name")
		elif(args[0]=="!saveconfig"):
			self.say(c, "Saving config...")
			f=open("config.py", "a")
			f.write("# Automatic config save on "+time.asctime()+"\n")
			f.write("owners=[\""+("\",\"".join(self.owners))+"\"]\n")
			f.write("channels=[\""+("\",\"".join(self.channelList))+"\"]\n")
			f.write("nick=\""+self._nickname+"\"\n")
			f.write("templates=[\""+("\",\"".join(templates))+"\"]\n")
			f.flush()
			f.close()
			self.say(c, "Config saved!")
		elif(args[0]=="!say"):
			try:
				self.say(args[1], " ".join(args[2:]))
			except:
				self.say(c, "Usage: !say nick_or_channel message")
		elif(args[0]=="!help"):
			if(len(args)>1):
				if(args[1] in ["quit", "save", "load", "regenLines", "saveconfig"]):
					self.say(c, args[1]+" does not take args")
				else:
					self.say(c, "Please run !"+args[1]+" without any args to see usage information")
			else:
				self.say(c, "Available commands are: quit, save, load, regenLines, replyrate, tagfrequency, join, part, rejoin, nick, say, addowner, rmowner, saveconfig, and help")
	def say(self, c, resp):
		time.sleep(1)
		for line in resp.split("\n"):
			try:
				if(len(line)>500):
					while len(line)>500:
						pre=line[:500]
						line=line[500:]
						self.logAndPrint("->\t"+c+"\t<"+self._nickname+"> "+pre)
						self.connection.privmsg(c, pre)
						time.sleep(1)
				self.logAndPrint("->\t"+c+"\t<"+self._nickname+"> "+line)
				self.connection.privmsg(c, line)
				time.sleep(2)
			except irclib.ServerNotConnectedError as err:
				print(str(err))
				self.autosave()
				self.saveconfig()
				time.sleep(30)
				self.start()
			except:
				print("Could not send message!")
				print(sys.exc_info())
		
	def rejoin(self):
		self.logAndPrint("-- Joining channels: "+(" ".join(self.channelList)))
		for chan in self.channelList:
			self.connection.join(chan)
			time.sleep(1)
	def on_welcome(self, c, e):
		self.logAndPrint("-- Connecting")
		if(self.password):
			self.logAndPrint("-- Identifying")
			self.connection.privmsg("nickserv", "identify "+self.password)
			time.sleep(5)
		if(len(templates)>0):
			self.logAndPrint("-- Loading templates")
			for template in templates:
				self.logAndPrint("-- Loading template "+str(template))
				markov.loadTemplateRuleset(template)
		self.logAndPrint("-- Loading markov model")
		markov.load()
		self.rejoin()
	def on_nicknameinuse(self, c, e):
		self._nickname="_"+self._nickname
		self.connection.nick(self._nickname)

try:
	from config import servers, nick, realname, owners, channels, password
	from config import *
except:
	f=open("config.py", "w")
	f.write("""# AUTOGENERATED BY YABOT
servers=[("irc.freenode.com", 6667)]
nick="YeahBot"
realname="Mark V. Shaney"
owners=["enkiv2", "enki-2", "ENKI-]["]
channels=["##politics"]
password=""
templates=[]
""")
	f.close()

def main():
	bot=YaBot(servers, nick, realname, owners, channels, password)
	try:
		bot.start()
	except Exception as e:
                print(e)
		os.rename("yabot_state.pickle", "yabot_state.pickle."+str(time.time()))
		markov.save()
if __name__=="__main__":
	main()

