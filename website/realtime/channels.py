from django.conf import settings
from twisted.internet import reactor, protocol
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.python import log
from txredis.protocol import Redis, RedisClientFactory, RedisSubscriber

from canvas import util


class RedisDispatch(object):
    def __init__(self, host, port):
        self._subscriptions = {}
        reactor.connectTCP(host, port, RedisDispatchFactory(self))

    def clientConnected(self):
        # Resubscribe to any channels.
        # Messages inbetween have been dropped :(
        for channel in self._subscriptions.iterkeys():
            self.redis.subscribe(str(channel))   

    def subscribe(self, channel, receiver):
        channel = str(channel)
        self._subscriptions[channel] = receiver
        self.redis.subscribe(channel)

    def unsubscribe(self, channel):
        channel = str(channel)
        try:
            del self._subscriptions[channel]
        except KeyError:
            pass
        else:    
            self.redis.unsubscribe(channel)

    def messageReceived(self, channel, message):
        self._subscriptions[channel].messageReceived(message)


class DisconnectedRedis(object):
    def subscribe(self, channel):
        pass
        
    def unsubscribe(self, channel):
        pass


class RedisDispatchSubscriber(RedisSubscriber):
    def __init__(self, dispatch):
        RedisSubscriber.__init__(self)
        self.dispatch = dispatch
        
    def connectionMade(self):
        RedisSubscriber.connectionMade(self)
        self.dispatch.clientConnected()
        
    def messageReceived(self, channel, message):
        self.dispatch.messageReceived(channel, message)


class RedisDispatchFactory(protocol.ReconnectingClientFactory):
    maxDelay = 5.0
    
    def __init__(self, dispatch):
        self.dispatch = dispatch

    def buildProtocol(self, addr):
        print "Connected to redis."
        self.resetDelay()
        self.dispatch.redis = RedisDispatchSubscriber(self.dispatch)
        return self.dispatch.redis

    def clientConnectionLost(self, connector, reason):
        print "WARNING: Redis Subscription Connection Lost. Probably dropping messages!"
        self.dispatch.redis = DisconnectedRedis()
        protocol.ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        print "WARNING: Redis Subscription Failed to Reconnect. Probably still dropping messages!"
        protocol.ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)


class Channel(object):
    timeout = 5
    
    class DisconnectedError(RuntimeError):
        pass
    
    class ChannelState(object):
        pass
        
    connected = ChannelState()
    timing_out = ChannelState()
    disconnected = ChannelState()
    
    def __init__(self, services, redis_channel):
        self.svc = services
        self.id = self.rc = redis_channel
        self._participants = set()
        self.connect()
        
    def connect(self):
        self.svc.redis_sub.subscribe(self.rc.pubsub, self)
        self.state = Channel.connected
        
    def disconnect(self):
        self.state = Channel.disconnected
        self.svc.redis_sub.unsubscribe(self.rc.pubsub)
        
    def cancel_timeout(self):
        if self.state == Channel.timing_out:
            self.timeout_call.cancel()
            self.state = Channel.connected
        elif self.state == Channel.disconnected:
            self.connect()

    def join(self, listener):
        if self.state == Channel.timing_out:
            self.cancel_timeout()
        elif self.state == Channel.disconnected:
            self.connect()
            
        self._participants.add(listener)
        listener.channels.add(self)

    @inlineCallbacks
    def backlog(self, start=-1):
        try:
            raw_json = yield self.svc.redis.zrangebyscore(self.rc.msg_backlog.key, start + 1, count=100, withscores=True)
        except RuntimeError:
            raise Channel.DisconnectedError
        messages = [{'id': int(id), 'payload': util.loads(payload)} for (payload, id) in raw_json]
        if not messages: returnValue({})
        else: returnValue({self.rc.channel: messages})

    def leave(self, listener):
        try:
            self._participants.remove(listener)
        except KeyError:
            pass
            
        try:
            listener.channels.remove(self)
        except KeyError:
            pass
        
        if not self._participants and self.state == Channel.connected:
            self.state = Channel.timing_out
            self.timeout_call = reactor.callLater(self.timeout, self.disconnect)
            
    def messageReceived(self, raw):
        message = util.loads(raw)
        for participant in list(self._participants):
            participant.send({self.rc.channel: [message]})
            self.leave(participant)


class ObjectManager(object):
    def __init__(self, services, factory):
        self.objects = {}
        self.factory = factory
        self.services = services

    def new(self, id):
        obj = self.factory(self.services, id)
        self.objects[id] = obj
        return obj

    def get(self, id):
        obj = self.objects.get(id, None)
        if obj is None:
            return self.new(id)
        else:
            return obj
            
    def remove(self, obj):
        if self.objects.get(obj.id) == obj:
            del self.objects[obj.id]


class RedisServiceRegisteringFactory(RedisClientFactory):
    # Note: RedisClientFactory is a ReconnectingClientFactory
    maxDelay = 5.0
    
    def __init__(self, services, *args, **kwargs):
        RedisClientFactory.__init__(self, *args, **kwargs)
        self.services = services
        
    def buildProtocol(self, addr):
        print "Connected to redis (Command Connection)."
        protocol = RedisClientFactory.buildProtocol(self, addr)
        self.services.redis = protocol
        return protocol

    def clientConnectionLost(self, connector, reason):
        print "WARNING: Redis Command Connection Lost. Probably dropping messages!"
        RedisClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        print "WARNING: Redis Command Connection Failed to Reconnect. Probably still dropping messages!"
        RedisClientFactory.clientConnectionFailed(self, connector, reason)        


class Services(object):
    def __init__(self):
        self.channels = ObjectManager(self, Channel)
        
    @inlineCallbacks
    def connect(self):  
        cc = lambda *args: protocol.ClientCreator(reactor, *args)

        self.redis_sub = RedisDispatch(settings.REDIS_HOST, settings.REDIS_PORT)
        redis_factory = RedisServiceRegisteringFactory(self)
        reactor.connectTCP(settings.REDIS_HOST, settings.REDIS_PORT, redis_factory)
        yield redis_factory.deferred

