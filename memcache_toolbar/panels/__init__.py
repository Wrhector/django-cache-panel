from datetime import datetime
from pprint import pprint
import logging

logger = logging.getLogger(__name__)

try:
    import pylibmc
    import _pylibmc

    # duplicating the client code sucks so hard, but it's necessary since the
    # original uses super and we'd need to inherit from it and then replace it
    # resulting in a class that inherits from itself :( see
    # http://fuhm.net/super-harmful/ anyway, see the bottom of this class for
    # the methods we're installing tracking on
    class TrackingClient(_pylibmc.client):
        def __init__(self, servers, binary=False):
            """Initialize a memcached client instance.

            This connects to the servers in *servers*, which will default to being
            TCP servers. If it looks like a filesystem path, a UNIX socket. If
            prefixed with `udp:`, a UDP connection.

            If *binary* is True, the binary memcached protocol is used.
            """
            self.binary = binary
            self.addresses = list(servers)
            addr_tups = []
            for server in servers:
                addr = server
                port = 11211
                if server.startswith("udp:"):
                    stype = _pylibmc.server_type_udp
                    addr = addr[4:]
                    if ":" in server:
                        (addr, port) = addr.split(":", 1)
                        port = int(port)
                elif ":" in server:
                    stype = _pylibmc.server_type_tcp
                    (addr, port) = server.split(":", 1)
                    port = int(port)
                elif "/" in server:
                    stype = _pylibmc.server_type_unix
                    port = 0
                else:
                    stype = _pylibmc.server_type_tcp
                addr_tups.append((stype, addr, port))
            _pylibmc.client.__init__(self, servers=addr_tups, binary=binary)

        def __repr__(self):
            return "%s(%r, binary=%r)" % (self.__class__.__name__,
                                          self.addresses, self.binary)

        def __str__(self):
            addrs = ", ".join(map(str, self.addresses))
            return "<%s for %s, binary=%r>" % (self.__class__.__name__,
                                               addrs, self.binary)

        def get_behaviors(self):
            """Gets the behaviors from the underlying C client instance.

            Reverses the integer constants for `hash` and `distribution` into more
            understandable string values. See *set_behaviors* for info.
            """
            bvrs = _pylibmc.client.get_behaviors(self)
            bvrs["hash"] = hashers_rvs[bvrs["hash"]]
            bvrs["distribution"] = distributions_rvs[bvrs["distribution"]]
            return BehaviorDict(self, bvrs)

        def set_behaviors(self, behaviors):
            """Sets the behaviors on the underlying C client instance.

            Takes care of morphing the `hash` key, if specified, into the
            corresponding integer constant (which the C client expects.) If,
            however, an unknown value is specified, it's passed on to the C client
            (where it most surely will error out.)

            This also happens for `distribution`.
            """
            behaviors = behaviors.copy()
            if behaviors.get("hash") is not None:
                behaviors["hash"] = hashers[behaviors["hash"]]
            if behaviors.get("ketama_hash") is not None:
                behaviors["ketama_hash"] = hashers[behaviors["ketama_hash"]]
            if behaviors.get("distribution") is not None:
                behaviors["distribution"] = distributions[behaviors["distribution"]]
            return _pylibmc.client.set_behaviors(self, behaviors)

        behaviors = property(get_behaviors, set_behaviors)
        @property
        def behaviours(self):
            raise AttributeError("nobody uses british spellings")

        # methods we're adding tracking to

        def get(self, *args, **kwargs):
            return _pylibmc.client.get(self, *args, **kwargs)

        def get_multi(self, *args, **kwargs):
            return _pylibmc.client.get_multi(self, *args, **kwargs)

        def set(self, *args, **kwargs):
            return _pylibmc.client.set(self, *args, **kwargs)

        def set_multi(self, *args, **kwargs):
            return _pylibmc.client.set_multi(self, *args, **kwargs)

        def add(self, *args, **kwargs):
            return _pylibmc.client.add(self, *args, **kwargs)

        def replace(self, *args, **kwargs):
            return _pylibmc.client.replace(self, *args, **kwargs)

        def append(self, *args, **kwargs):
            return _pylibmc.client.append(self, *args, **kwargs)

        def prepend(self, *args, **kwargs):
            return _pylibmc.client.prepend(self, *args, **kwargs)

        def incr(self, *args, **kwargs):
            return _pylibmc.client.incr(self, *args, **kwargs)

        def decr(self, *args, **kwargs):
            return _pylibmc.client.decr(self, *args, **kwargs)

        def delete(self, *args, **kwargs):
            return _pylibmc.client.delete(self, *args, **kwargs)

        def delete_multi(self, *args, **kwargs):
            return _pylibmc.client.delete_multi(self, *args, **kwargs)

        def flush_all(self, *args, **kwargs):
            return _pylibmc.client.flush_all(self, *args, **kwargs)

    if pylibmc.Client.__name__ == 'Client':
        logger.debug('installing pylibmc.Client with tracking')
        pylibmc.Client = TrackingClient

except:
    logger.debug('unable to install pylibmc.Client with tracking')
