#!/usr/bin/env python3

"""Helper code for retrieving information from the remote support server."""

import sys
import os
import requests
import http
import json
import enum

_mirs_host = 'mirs.mti.local'

class PrintUsage(Exception):
    def __init__(self):
        return super().__init__()        


class MalformedFilename(Exception):
    def __init__(self, path):
        super().__init__()
        self.path = path
        return
    def __str__(self):
        return f"{super().__str__()} Malformed path: {self.path}"

class TooManyHosts(Exception):
    def __init__(self):
        return super().__init__()        
    def __str__(self):
        return f"You may only specify one host."

class TooManyUsers(Exception):
    def __init__(self):
        return super().__init__()        
    def __str__(self):
        return f"You may only specify one user account."


class UnsupportedUsers(Exception):
    def __init__(self, allowed):
        super().__init__()
        self.allowed = allowed
    def __str__(self):
        return f"Only the following users are supported: {self.allowed}."


class UnspecifiedHost(Exception):
    def __init__(self):
        return super().__init__()        
    def __str__(self):
        return f"You must a host for the copy."


    
class MirsClientNotFound(Exception):
    def __init__(self, miec):
        super().__init__()
        self.miec = miec
        return
    def __str__(self):
        return f"{super().__str__()} Unknown system {self.miec}"

def all_tunnels(mirs_server=_mirs_host, rest_port=8080):
    """
    Retrieve a list of all tunnels.

    Return
        Dictionary of tunnels.  The key of each item is the name of
        the system.  The data in each item is itself a dictionary with
        the miec port number as the key, the mirs port number as the
        data.  Example:
          {'CR-713':      {'47101': 40861, 
                           '2222':  52389}, 
           'Cryostation': {'22':   45861, 
                           '2222': 49861, 
                           '5900': 50861}}
    """
    result = json.loads(requests.get(f'http://{mirs_server}:{rest_port}/tunnels').content.decode('utf-8'))
    return result;

def all_ips(mirs_server=_mirs_host, rest_port=8080):
    """
    Retrieve a list of each system and its IP address

    Return
        Dictionary of system:ip values
        Example:
          {'CR-732': '128.174.165.72', 
           'CR-801': '206.196.177.114',
           ...}

    """
    result = json.loads(requests.get(f'http://{mirs_server}:{rest_port}/ips').content.decode('utf-8'))
    return result;

def lookup_port(miec, miec_port, mirs_server=_mirs_host, rest_port=8080):
    """Lookup port on mirs server for tunneling into the MIEC.
    
    Keyword Parameters
      miec         The name of the MIEC to attach to (e.g. CR-712)
      miec_port    Port on the MIEC to attach to 
      mirs_server  The remote support server.  (i.e. the computer running 
                   tunnel_display.)
      rest_port    Port number
    """
    if isinstance(miec_port, enum.Enum): miec_port = miec_port.value
    tunnels = all_tunnels()
    try:
        if miec not in tunnels:
            for k in tunnels.keys(): miec = k if k.lower()==miec.lower() else miec                
        return tunnels[miec][str(miec_port)]
    except KeyError:
        pass
    raise MirsClientNotFound(miec)

def rewrite_ssh_args(argv, mirs_server=_mirs_host):
    """Rewrite the ssh arguments to run through the MIRS tunnel. 
    """
    cmd = os.path.basename(argv[0])

    if cmd=='mirs-scp':
        flags   = ['-3', '-4', '-6', '-B', '-C', '-p', '-q', '-r', '-v']
        options = ['-c cipher', '-F ssh_config', '-i identity_file',
                   '-l limit', '-o ssh_option', '-P port', '-S program']
        result = ['scp', '-o' 'StrictHostKeyChecking=no']
    else:
        flags   = ["-4", "-6", "-A", "-a", "-C", "-f", "-G", "-g", "-h", "-K",
                   "-k", "-M", "-N", "-n", "-q", "-s", "-T", "-t", "-V", "-v",
                   "-X", "-x", "-Y", "-y"]
        options = ["-b", "-c", "-D", "-E", "-e", "-F", "-I", "-i", "-J", "-L",
                   "-l", "-m", "-O", "-o", "-p", "-Q", "-R", "-S", "-W", "-w"]
        result = ['ssh', '-o' 'StrictHostKeyChecking=no']

    i = 1
    while i<len(argv):
        if argv[i] in flags or argv[i]=='--help':
            result.append(argv[i])
            if argv[i] in ('-h', '--help'): raise PrintUsage()
            if argv[i]=='-3':
                sys.stderr.write("Error: 3-way copies are not supported\n")
                raise PrintUsage()
            if argv[i] in ('-p', '-P'):
                sys.stderr.write("Error: Specifying an alternate port is not supported\n")
                raise PrintUsage()
        elif argv[i] in options:
            result.append(argv[i])
            i = i+1
            result.append(argv[i])
        elif argv[i][:2] in options:
            result.append(argv[i])
        else:
            #
            # We've hit the end of the flags and options.  For scp argv[i] is
            # the name of the host.  The arguments after that (if any)
            # are the name of a command and its command line arguments.
            #
            # For scp the remaining arguments have hostnames and need
            # to be rewritting accordingly
            #
            if result[0]=='ssh':
                if '-6' not in argv: result.append('-4')
                result.append('-p')
                result.append(f'{lookup_port(argv[i], 2222, mirs_server)}')
                result.append(f'mi@{mirs_server}')
                result = result + argv[i+1:]
            else:                    
                def _split_scp_fname(fname):
                    user = ''
                    host = ''
                    if fname.find('@') > fname.find(':'):           raise MalformedFilename(fname)
                    if fname.find('@')!=-1 and fname.find(':')==-1: raise MalformedFilename(fname)
                    if fname.find('@')!=-1:
                        user  = fname[:fname.find('@')] + '@'
                        fname = fname[fname.find('@')+1:]
                    if fname.find(':')!=-1:
                        host  = fname[:fname.find(':')] + ':'
                        fname = fname[fname.find(':')+1:]
                    result = [user, host, fname]
                    return result
                def _find_scp_port(fnames):
                    hosts = [h for h in [_split_scp_fname(f)[1] for f in fnames] if h]
                    if len(hosts)==0: raise UnspecifiedHost()
                    if len(hosts)>1:  raise TooManyHosts()
                    return lookup_port(hosts[0][:-1], 2222, mirs_server)
                def _find_scp_user(fnames):
                    users = [u for u in list({_split_scp_fname(f)[0]:0 for f in fnames}) if u]
                    if len(users)==0: users = ['mi@']
                    if len(users)>1:  raise TooManyUsers()
                    return users[0][:-1]
                def _convert_scp_filenames(fnames, user):
                    altered_names = []
                    for f in fnames: 
                        tmp = _split_scp_fname(f)
                        if len(tmp[1])>0:
                            tmp[1] = mirs_server + ':'
                            tmp[0] = user + '@'
                        altered_names.append(''.join(tmp))
                    return altered_names

                fnames = argv[i:]
                result.append('-P')
                result.append(str(_find_scp_port(fnames)))
                              
                result = result + _convert_scp_filenames(fnames, _find_scp_user(fnames))
            break
        i = i+1
    return result

if __name__ == "__main__":
    print(f"all_tunnels is {all_tunnels(_mirs_host)}")
    print(f"all_ips is {all_ips(_mirs_host)}")
    
    
