# Legobot
# Copyright (C) 2016 Brenton Briggs, Kevin McCabe, and Drew Bronson

import ssl
import threading
import logging

import irc.bot
import irc.client
import irc.connection

from Legobot.Message import *
from Legobot.Lego import Lego
from jaraco.stream import buffer

logger = logging.getLogger(__name__)


class IgnoreErrorsBuffer(buffer.DecodingLineBuffer):
    """  Handle char decode errors better
    """
    def handle_exception(self):
        pass
irc.client.ServerConnection.buffer_class = IgnoreErrorsBuffer
irc.client.SimpleIRCClient.buffer_class = IgnoreErrorsBuffer

class IRCBot(threading.Thread, irc.bot.SingleServerIRCBot):
    """
    Create bot instance
    """
    def __init__(self, baseplate, channels, nickname, server,
                 port=6667, use_ssl=False, password=None,
                 username=None, ircname=None):
        irc.bot.SingleServerIRCBot.__init__(self,
                                            [(server, port)],
                                            nickname,
                                            nickname)
        threading.Thread.__init__(self)

        # the obvious self.channels is already used by irc.bot
        self.my_channels = channels
        self.nickname = nickname
        self.server = server
        self.baseplate = baseplate
        self.port = port
        self.use_ssl = use_ssl
        self.password = password
        self.username = username
        self.ircname = ircname

    def connect(self, *args, **kwargs):
        """
        Connect to a server.

        This overrides the function in SimpleIRCClient
        to provide SSL functionality.

        :param args:
        :param kwargs:
        :return:
        """
        if self.use_ssl:
            factory = irc.connection.Factory(wrapper=ssl.wrap_socket)
        else:
            factory = irc.connection.Factory()
        self.connection.connect(server=self.server,
                                port=self.port,
                                nickname=self.nickname,
                                connect_factory=factory,
                                password=self.password,
                                username=self.username,
                                ircname=self.ircname)

    def on_pubmsg(self, c, e):
        """
        This function runs when the bot receives a public message.
        """
        text = e.arguments[0]
        metadata = Metadata(source=self).__dict__
        metadata['source_channel'] = e.target
        message = Message(text=text, metadata=metadata).__dict__
        self.baseplate.tell(message)

    def on_welcome(self, c, e):
        """
        This function runs when the bot successfully connects to the IRC server
        """
        for channel in self.my_channels:
            logger.debug('Attempting to join %s' % channel)
            c.join(channel)

    def run(self):
        """
        Run the bot in a thread.

        Implementing the IRC listener as a thread allows it to
        listen without blocking IRCLego's ability to listen
        as a pykka actor.

        :return: None
        """
        self._connect()
        super(irc.bot.SingleServerIRCBot, self).start()


class IRC(Lego):

    def __init__(self, baseplate, lock, *args, **kwargs):
        super().__init__(baseplate, lock)
        self.botThread = IRCBot(baseplate, *args, **kwargs)

    def on_start(self):
        self.botThread.start()

    def listening_for(self, message):
        return str(self.botThread) != str(message['metadata']['source'])

    def handle(self, message):
        logger.info(message)
        self.botThread.connection.privmsg(message['metadata']['opts'][
            'target'], message['text'])

    def get_name(self):
        return None
