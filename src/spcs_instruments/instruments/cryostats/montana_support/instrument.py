#!/usr/bin/env python3
#
# Class to simplify RESTful API communication with all Montana Instruments instruments.
#
# Example usage:
#  import instrument
#  inst = instrument.Instrument('192.168.45.123', port='47101', version='v1')
#  inst.call_method('/controller/methods/cooldown()')
#
import os
import os.path as op
import sys
sys.path.append(op.abspath(op.join(op.dirname(__file__), os.pardir, os.pardir, 'commonScripting', 'pythonlibs')))

from enum import IntEnum
import requests
import json
import re
import time

from . import ssh_tunnel
import socket
import http

from . import mirs_helpers

_force_ipv4 = True  # Some day IPv6 will be ubiquitous.  Today is not that day.

_success = range(200,300)

class Rest_Ports(IntEnum):
    """Constants for TCP port numbers of the various REST servers
    """
    scryostation_hlm       = 47101  # /etc/services entry is "cryo-hlm             47101/tcp"
    cryocore_hlm           = 47101  # /etc/services entry is "cryo-hlm             47101/tcp"
    status_leds_llm        = 47102  # /etc/services entry is "statusleds-llm       47102/tcp"
    xpcryostation_hlm      = 47103  # /etc/services entry is "sub2k-hlm            47103/tcp"
    positioner_hlm         = 47104  # /etc/services entry is "positioner-hlm       47104/tcp"
    power_hub_llm          = 47105  # /etc/services entry is "powerhub-llm         47105/tcp"
    tcm_cal_llm            = 47107  # /etc/services entry is "tcmcal-llm           47107/tcp"

    temp_control1_llm      = 47111  # /etc/services entry is "tcm1-llm             47111/tcp"
    temp_control2_llm      = 47112  # /etc/services entry is "tcm2-llm             47112/tcp"
    temp_control3_llm      = 47113  # /etc/services entry is "tcm3-llm             47113/tcp"
    temp_control4_llm      = 47114  # /etc/services entry is "tcm4-llm             47114/tcp"
    temp_control5_llm      = 47115  # /etc/services entry is "tcm5-llm             47115/tcp"
    
    piezo_stepper1_llm     = 47121 # /etc/services entry is "piezostep1-llm        47121/tcp"
    piezo_stepper2_llm     = 47122 # /etc/services entry is "piezostep2-llm        47122/tcp"
    piezo_stepper3_llm     = 47123 # /etc/services entry is "piezostep3-llm        47123/tcp"
    piezo_stepper4_llm     = 47124 # /etc/services entry is "piezostep4-llm        47124/tcp"
    piezo_stepper5_llm     = 47125 # /etc/services entry is "piezostep5-llm        47125/tcp"
    
    pfeiffertc110_llm      = 47130 # /etc/services entry is "pfeiffertc110-llm     47130/tcp"
    
    cryostatancillary_llm  = 47135 # /etc/services entry is "cryostatancillary-llm 47135/tcp"
    
    massflow_llm           = 47140 # /etc/services entry is "massflow-llm          47140/tcp"

    mercury_hlm            = 47150 # /etc/services entry is "mercury-hlm           47150/tcp"

    keyencecl3000_llm      = 47160 # /etc/services entry is "keyencecl3000-llm     47160/tcp"
    keyencesift1000_llm    = 47161 # /etc/services entry is "keyencesift1000-llm   47161/tcp"
    
    mmc113_llm             = 47170 # /etc/services entry is "mmc113-llm            47170/tcp"
    lynx_hlm               = 47171 # /etc/services entry is "lynx-hlm              47171/tcp"

    
    chronos_hlm            = 47180  # /etc/services entry is "chronos-hlm          47180/tcp"

    pass


TunnelError = ssh_tunnel.TunnelError

class CouldNotConnect(Exception): pass

class NotConnected(Exception): pass

class BadUrl(Exception): pass

def _verifySuccess(op, path, resp) -> None:
    """Make sure the operation succeeded, otherwise throw ApiError exception

    Keyword arguments:
       op   -- REST operation that occurred
       path -- The URI of the operation
       resp -- Response from the server (body and HTTP response code)
    """
    if resp.status_code not in _success:
        # Something went wrong

        brief = None
        details = None
        try:
            if 'title' in resp.json().keys(): brief = resp.json()['title']
            if 'detail' in resp.json().keys(): details = resp.json()['detail']
        except:
            pass

        raise ApiError(op, path, resp.status_code, brief, details)

    return

def _rewrite_connection(ip, port, tunnel):
    """For hostnames that start with "mirs:" determine port on MIRS server

    If the user specified "mirs:somemachine" this routine will lookup 
    the corresponding secure tunnel on the MIRS server.

    If ip doesn't start with "mirs:" then ip, port, and tunnel are
    returned unchanged. 
    """
    
    if isinstance(ip, str):
        if ip.startswith("mirs:"):
            (miec, mirs) = (ip+":support").split(':')[1:3]
            try:
                (ip, port, tunnel) = (mirs, 
                                      mirs_helpers.lookup_port(miec, port, mirs_server=mirs),
                                      False)
            except mirs_helpers.MirsClientNotFound:
                pass
        elif _force_ipv4 and not re.match(r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$', ip):
            ip = socket.getaddrinfo(ip, None, socket.AF_INET)[0][4][0]
    return (ip, port, tunnel)
        
class Instrument:
    def __init__(self, ip, port, version, verbose=False, tunnel=False):
        """Create a base instrument object for Scripting R3

        Keyword arguments:
          ip      -- IP address (or hostname) of the instrument (e.g. an XP100).
                     To access the instrumnent through a remote access server
                     use a string like 
                        mirs:<miec>:<name or IP of server>
                     e.g. 
                        mirs:CR-713:support
                     If the name of the MIRS is omitted it defaults 
                     to support
          port    -- TCP Port number of the service on the MIEC.                     
          version -- REST API version (e.g. "v1")
          verbose -- Print debug information?
          tunnel  -- Communicate through a secure SSH tunnel?
        """
        assert not isinstance(port, (list,tuple)), "This class can only talk to a single port"

        self.tun     = None
        (self.ip, self.port, tunnel) = _rewrite_connection(ip, port, tunnel)

        self.version = version
        self.verbose = verbose

        if tunnel:
            try:
                self.tun  = ssh_tunnel.tunnel(remote_host = ip, remote_ports = port)
            except:
                raise TunnelError("Could not start the ssh tunnel.  Have you copied your ssh keys?")
            self.ip   = self.tun.local_bind_address[0]
            self.port = self.tun.local_bind_ports[0]
        return

    def close(self):
        if self.tun is not None:
            self.tun.stop()
        self.ip      = None
        self.port    = None
        self.version = None
        self.verbose = None
        self.tun     = None


    def __del__(self):
        self.close()
        return

    def __root_endpoint(self):
        """The portion common to all endpoints for this instrument.

        Example:
          self.__root_endpoint() -> "http://192.168.45.244:47101/v1"
        """
        return f'http://{self.ip}:{self.port}/{self.version}'

    def is_up(self):
        """Is the instrument responding?
        """
        result = False

        try:
            tmp = self.get("/version")
            result = True
        except ApiError:
            # 
            # An API error means the cryostation didn't like what we
            # sent it.  The fact that it doesn't like something means
            # it is up and running.
            # 
            result = True
        except http.client.RemoteDisconnected:
            self.close()
            pass
        except requests.exceptions.ConnectionError:
            self.close()
            pass
        except NotConnected:
            print("hit an instrument.NotConnected")
            self.close()
            pass            
        except:
            raise
        return result

    def url(self, path):
        if self.ip is None: raise NotConnected()

        root = self.__root_endpoint()

        path = path.strip('/')
        path = path.replace('//', '/')

        return f'{root}/{path}'

    def call_method(self, path, data=None):
        """Call a method to perform some action with the instrument.

        """
        uri = self.url(path)
        if (data is not None):
            if (self.verbose): print(f'POST {uri} [data -> {data}]')
            resp = requests.post(uri, json=data)
        else:
            if (self.verbose): print(f'POST {uri}')
            resp = requests.post(uri)

        _verifySuccess('POST', path, resp)

        c = resp.content.decode('utf-8')
        if c != '':
            return json.loads(c)

    def set_prop(self, path, data=None):
        uri = self.url(path)

        if (self.verbose): print(f'PUT {uri} [data -> {data}]')
        resp = requests.put(uri, json=data)

        _verifySuccess('PUT', path, resp)

        c = resp.content.decode('utf-8')
        if c != '':
            return json.loads(c)

    def get_prop(self, path, params=None):
        """Retrieve a property value via REST from the instrument

        Keyword arguments:
           path    The non-root portion of the URI.
                   e.g. "/controller1/thermometer/properties/sample"
           params  (optional) Any parameters that need to be passed
                   along in the GET message.
        """
        uri = self.url(path)
        if (self.verbose): print(f'GET {uri} [params -> {params}]')
        try:
            # print(f"uri is |{uri}|")
            resp = requests.get(uri, params)
        except requests.exceptions.InvalidURL:
            raise BadUrl() from None
        except requests.exceptions.ConnectionError:
            raise
        except requests.exceptions.InvalidURL:
            raise BadUrl()
        except:
            sys.stderr.write("unknown exception\n")
            sys.stderr.write(f"{sys.exc_info()}")
            raise

        _verifySuccess('GET', path, resp)

        c = resp.content.decode('utf-8')
        result = None
        if c != '': result = json.loads(c)

        return result

    def get(self, path, params=None):
        """Deprecated.  Use get_prop() instead."""
        return self.get_prop(path, params)


class ApiError(Exception):
    """An API Error Exception"""

    def __init__(self, op, path, response_code, brief, details):
        """Create an error object.

        Note- Normally this is not directly called.  The wrapper
        _verifySuccess will, if needed, create and raise this
        type of exception.

        Keyword arguments:
           op            -- REST operation that triggered the error (e.g. "GET").
           path          -- The URI that triggered the error.
           response_code -- The HTTP response code (e.g. 400)
           brief            A synopsis of the problem.  Often it is the
                            contents of the "title" field of message content.
           details       -- A description of the problem.  Often it is the
                            contents of the "detail" field of message content.
        """
        self.op            = op
        self.path          = path
        self.response_code = response_code
        self.brief         = brief
        self.details       = details
        return

    def __str__(self):
        result = f"ApiError: {self.op}: {self.response_code}"
        if self.brief: result = f"ApiError: {self.op}: {self.response_code}: {self.brief}"
        return result
