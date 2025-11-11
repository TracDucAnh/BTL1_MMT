# reverse_proxy.py
#
# Copyright (C) 2025 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course,
# and is released under the "MIT License Agreement". Please see the LICENSE
# file that should have been included as part of this package.
#
# WeApRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#


"""
start_proxy
~~~~~~~~~~~~~~~~~

This module serves as the entry point for launching a proxy server using Python's socket framework.
It parses command-line arguments to configure the server's IP address and port, reads virtual host
definitions from a configuration file, and initializes the proxy server with routing information.

Requirements:
--------------
- socket: provide socket networking interface.
- threading: enables concurrent client handling via threads.
- argparse: parses command-line arguments for server configuration.
- re: used for regular expression matching in configuration parsing
- response: response utilities.
- httpadapter: the class for handling HTTP requests.
- urlparse: parses URLs to extract host and port information.
- daemon.create_proxy: initializes and starts the proxy server.

"""

import socket
import threading
import argparse
import re
from urllib.parse import urlparse
from collections import defaultdict
import os
from daemon import create_proxy

PROXY_PORT = 8080


def parse_virtual_hosts(config_file):
    """
    Parses virtual host blocks from a config file.

    :config_file (str): Path to the NGINX config file.
    :rtype list of dict: Each dict contains 'listen'and 'server_name'.
    """

    if not os.path.exists(config_file):
        raise FileNotFoundError(f"Config file {config_file} not found.")


    with open(config_file, 'r') as f:
        config_text = f.read()

    # Match each host block
    host_blocks = re.findall(r'host\s+"([^"]+)"\s*\{(.*?)\}', config_text, re.DOTALL)

    if len(host_blocks) == 0:
        raise ValueError("No valid host blocks found in configuration file.")

    dist_policy_map = ""

    routes = {}

    for host, block in host_blocks:
        proxy_map = {}
        # Find all proxy_pass entries
        proxy_passes = re.findall(r'proxy_pass\s+http://([^\s;]+);', block)
        if not proxy_passes:
            print(f"[WARN] No proxy_pass found for host '{host}'. Skipped.")
            continue
        map = proxy_map.get(host,[])
        map = map + proxy_passes
        proxy_map[host] = map

        # Find dist_policy if present (fixed regex)
        policy_match = re.search(r'dist_policy\s+([A-Za-z0-9\-_]+)', block)
        if policy_match:
            dist_policy_map = policy_match.group(1).strip()
        else: # default policy is round-robin
            dist_policy_map = 'round-robin'
            
        #
        # @bksysnet: Build the mapping and policy
        # TODO: this policy varies among scenarios 
        #       the default policy is provided with one proxy_pass
        #       In the multi alternatives of proxy_pass then
        #       the policy is applied to identify the highes matching
        #       proxy_pass
        #

        if len(proxy_map.get(host,[])) == 1:
            routes[host] = (proxy_map.get(host,[])[0], dist_policy_map)
        # else if:
        #         TODO:  apply further policy matching here

        else:
            policy_lower = dist_policy_map.lower()
            if policy_lower == "round-robin":
                routes[host] = (proxy_map.get(host, []), "round-robin")
            elif policy_lower == "least_conn":
                routes[host] = (proxy_map.get(host, []), "least_conn")
            elif policy_lower == "random":
                routes[host] = (proxy_map.get(host, []), "random")
            else:
                print(f"[WARN] Unknown policy '{dist_policy_map}' for host '{host}', fallback to round-robin.")
                routes[host] = (proxy_map.get(host,[]), "round-robin")

    for key, value in routes.items():
        print (key, value)
    
    for key in routes.keys():
        print(f"[INFO] Loaded route for host '{key}': {routes[key]}")

    return routes


if __name__ == "__main__":
    """
    Entry point for launching the proxy server.

    This block parses command-line arguments to determine the server's IP address
    and port. It then calls `create_backend(ip, port)` to start the RESTful
    application server.

    :arg --server-ip (str): IP address to bind the server (default: 127.0.0.1).
    :arg --server-port (int): Port number to bind the server (default: 9000).
    """

    parser = argparse.ArgumentParser(prog='Proxy', description='', epilog='Proxy daemon')
    parser.add_argument('--server-ip', default='0.0.0.0')
    parser.add_argument('--server-port', type=int, default=PROXY_PORT)
 
    args = parser.parse_args()
    ip = args.server_ip
    port = args.server_port

    routes = parse_virtual_hosts("config/proxy.conf")

    create_proxy(ip, port, routes)
