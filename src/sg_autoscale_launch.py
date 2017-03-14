#!/usr/bin/env python


import os
import re
import socket
import urllib2
import argparse
import cbbootstrap
from string import Template
import sys
import sg_launch

"""
The purpose of this script is to relaunch sync gateway with the correct config

- It uses cb-bootstrap in order to discover couchbase server IP

"""


def relaunch_sg_with_custom_config(stack_name, server_type, config_url):

    # Use cbbootrap to call REST API to discover the IP address of the initial couchbase server node
    couchbase_server_ip = cbbootstrap.discover_initial_couchbase_server_ip(stack_name)

    response = urllib2.urlopen(config_url)
    config_content = response.read()
    template = Template(config_content)
    sync_gateway_config_rendered = "Error"
    sg_accel_config_rendered = "Error"

    if server_type == sg_launch.SERVER_TYPE_SYNC_GATEWAY:
        sync_gateway_config_rendered = template.substitute(couchbase_server_ip=couchbase_server_ip)
    elif server_type == sg_launch.SERVER_TYPE_SG_ACCEL:
        sg_accel_config_rendered = template.substitute(couchbase_server_ip=couchbase_server_ip)
    else:
        raise Exception("Unrecognized server type: {}".format(server_type))

    sg_launch.main(
        sync_gateway_config_rendered,
        sg_accel_config_rendered,
        server_type,
    )


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--stack-name",
        help="The name of the cloudformation stack, so that cbbootstrap can discover couchbase server IP address",
        required=True,
    )
    parser.add_argument(
        "--server-type",
        help="The server type: sg or sg-accel",
        required=True,
    )
    parser.add_argument(
        "--config-url",
        help="The URL of the Sync Gateway or SG Accel configuration template.  It's expected to have $couchbase_server_ip placeholders which will be replaced by Couchbase Server IP addresses",
        required=True,
    )

    args = parser.parse_args()

    print("{} called with stack name: {}  server type: {} config url: {}".format(sys.argv[0], args.stack_name, args.server_type, args.config_url))

    relaunch_sg_with_custom_config(
        stack_name=args.stack_name.strip(),
        server_type=args.server_type.strip(),
        config_url=args.config_url.strip(),
    )



   
   
