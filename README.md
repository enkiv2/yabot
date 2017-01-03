# YABot
Yet Another chatBot

(Forked from [enkiv2/misc/yabot](http://github.com/enkiv2/misc/tree/master/yabot))

YABot is an irc bot that combines several different response generation methods. It is in python.

To run:

    ./main.py

During the first execution, this will generate a default configuration file ("config.py"); you should modify this configuration file before running again.

YABot takes commands (lines beginning with '!') from people with nicks in the 'owners' list, both in-channel and in private messages. Available commands are: quit, save, load, regenLines, replyrate, tagfrequency, join, part, rejoin, nick, say, addowner, rmowner, saveconfig, and help.

Supported methods of response generation are: markov chain, [phrase-chain](http://github.com/enkiv2/misc/tree/master/phrasechain) (by both sentences & lines), and eliza.

