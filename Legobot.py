import sys
import socket
import select
import string

class legoBot():
  def __init__(self,host,port,nick,rooms, logfcns = ""):
    self.host = host
    self.port = port
    self.nick = nick
    self.rooms = rooms
    self.logfcns = logfcns
    self.fcns = {}
  
  def addFcns(self, name, fcns):
    #name should be str, fcns should be a function object
    self.fcns[name] = fcns
  
  def addMassFcns(self, d):
    #merge a dictionary into fcns dicts
    self.fcns.update(d)
  
  def connect(self):
    self.connection = socket.socket()
    self.connection.connect((self.host, self.port))
    self.connection.sendall("NICK %s\r\n" % self.nick)
    self.connection.sendall("USER %s %s %s :%s\r\n" % (self.nick, self.nick, self.nick, self.nick))
    for room in self.rooms:
      self.connection.sendall("JOIN %s\r\n" % room)
    self.__listen()
  
  def sendMsg(self, msgToSend):
    self.connection.sendall(msgToSend)
  
  def __listen(self):
    while 1:
      if select.select([self.connection],[],[],1.0)[0]:
        readbuffer = self.connection.recv(1024)
        print readbuffer
        #split into lines
        temp = string.split(readbuffer, "\n")
        
        #iterate through any lines received
        for line in temp:
          if len(line.strip(' \t\n\r')) == 0:
            continue
          msg = Message(line)
          reply = msg.read(self.host, self.fcns, self.nick, self.logfcns)
          if reply:
            self.connection.sendall(reply)

class Message():
  def __init__(self, message):
    self.splitMessage = message.strip("\r").split(" ",7)
    self.length = len(self.splitMessage)
    self.userInfo = None
    self.actualUserName = None
    self.target = None
    self.cmd = None
    self.arg1 = None
    self.arg2 = None
    self.arg3 = None
      
  def read(self,host, fcns, nick, logfcns):
    self.host = host
    if self.splitMessage[0][0:4] == "PING":
      return self.reply(host, {}, nick)
      
    else:
      try:
        self.userInfo = self.splitMessage[0].lower()
        self.actualUserName = self.splitMessage[0][1:self.splitMessage[0].find("!")].lower()
        self.target = self.splitMessage[2].lower()
        self.cmd = self.splitMessage[3].lower()
        self.arg1 = self.splitMessage[4].lower()
        self.arg2 = self.splitMessage[5].lower()
        self.arg3 = self.splitMessage[6].lower()
      except:
        pass
      
      if logfcns:
        #pass line to our logging fcns
        logfcns(self)
        
      return self.reply(host, fcns, nick)
        
  def reply(self, host, fcns, nick):
    if self.splitMessage[0][0:4] == "PING":
      return "PONG :%s\r\n" % host
    
    if self.cmd:
      if self.cmd[1:] in fcns:
        returnVal, returnRoom = fcns[self.cmd[1:]](self)        
        if returnVal and returnRoom:
          #respond to room/person that function told us to
          return "PRIVMSG %s :%s\r\n" % (returnRoom, returnVal)
          
        elif returnVal and self.target.lower() == nick.lower():
          #if no room/person and it's a PM, reply to a PM with a PM
          return "PRIVMSG %s :%s\r\n" % (self.actualUserName, returnVal)
          
        elif returnVal and not returnRoom:
          #if no room/person returned just respond back to same room
          return "PRIVMSG %s :%s\r\n" % (self.target, returnVal)

  def __len__(self):
    return self.length
