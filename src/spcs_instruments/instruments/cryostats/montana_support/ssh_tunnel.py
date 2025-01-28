#!/usr/bin/env python3

"""Create an SSH tunnel for Scripting R3

The basic purpose of this is to run something that logically is
   ssh -N -L <local_port>:127.0.0.1:<remote_port> <remote_user>@<remote_host>
Internally it is implemented using sshtunnel.  See 
  https://github.com/pahaz/sshtunnel

"""

import sys
import os 
import subprocess
import time
import signal
import socket
import sshtunnel


class catch_sigint(object):
    def __init__(self):
        self.caught_sigint = False
    def note_sigint(self, signum, frame):
        self.caught_sigint = True
    def __enter__(self):
        self.oldsigint = signal.signal(signal.SIGINT, self.note_sigint)
        return self
    def __exit__(self, *args):
        signal.signal(signal.SIGINT, self.oldsigint)
    def __call__(self):
        return self.caught_sigint

class TunnelError(Exception):
    """Represent general SSH tunnel errors
    """
    def __init__(self, message):
        self.message = message
        return
    def __str__(self):
        return self.message
    
    
def tunnel(remote_host, remote_ports, remote_user="tunnel", local_ports=None):
    """Create an SSH tunnel

    Note- A background thread is implicitly created to handle the tunnel.

    Keyword Parameters: 
       remote_host   The name or IP number of the ECA system.
       remote_ports  A TCP port number (or a list)
       remote_user   The name of the remote user.  Defaults to "tunnel"
       local_ports   The local port to use (or list of ports).
                     A random port is choosen if local_port is None.

    Return: 
       server   The object that created the tunnel.  To get the 
                local port numbers look at
                server.local_bind_ports
    """ 

    def to_port_number(p):
        assert p is not None
        if isinstance(p, str):
            try:
                p = socket.getservbyname(p)
            except:
                p = int(p)
        return p
    
    if not isinstance(remote_ports, (list,tuple)): remote_ports = (remote_ports,)
    if isinstance(remote_ports, (list,)):          remote_ports = tuple(remote_ports)

    if local_ports is None:                       local_ports = (0,) * len(remote_ports)
    if not isinstance(local_ports, (list,tuple)): local_ports = (local_ports,)
    if isinstance(local_ports, (list,)):          local_ports = tuple(local_ports)

    assert len(local_ports) == len(remote_ports), "Must be a one to one mapping from local to remote"

    remote_binds = [('127.0.0.1', to_port_number(p)) for p in remote_ports]
    local_binds  = [('127.0.0.1', to_port_number(p)) for p in local_ports]

    
    pkey   = os.path.join(os.path.join(os.path.expanduser("~"), '.ssh'),
                          'id_rsa')
    server = sshtunnel.SSHTunnelForwarder(
        str(socket.gethostbyname(remote_host)),
        ssh_username          = remote_user,
        ssh_pkey              = pkey,
        local_bind_addresses  = local_binds,
        remote_bind_addresses = remote_binds,
        ssh_port              = 2222)
    try: 
        server.start()
    except sshtunnel.BaseSSHTunnelForwarderError as exc:
        raise TunnelError("Could not start tunnel.  Have you copied your ssh keys?") from None
    return server
    

def _main():
    running = True
    with catch_sigint() as got_sigint:
        ports  = (22, 2222, 2224, 5900, 47101, 47103, 47104)
        local  = None
        server = tunnel('192.168.45.115', ports, remote_user='tunnel', local_ports=local)
        print("started")
        print(f"remote->local ports are {[(ports[i], server.local_bind_ports[i]) for i in range(len(ports))]}")
        while running:
            try:
                print("sleeping")
                time.sleep(1)
                if got_sigint():
                    running = False
                    print("Caught Ctrl-C")
            except IOError:
                print("caught IOError")
                time.sleep(1)
                pass
            except KeyboardInterrupt:
                print("caught KeyboardInterrupt")
                time.sleep(1)
                pass
        try:
            server.stop()
            sys.exit(0)
        except:
            print("Caught exception trying to stop server")
            print(f"{sys.exc_info()}")
            sys.exit(1); 
    
if __name__=="__main__":
    _main()
            
                
        
            
                   
