#!/usr/bin/env python

import sg_launch
import os
import re
import socket
import argparse
import cbbootstrap
from string import Template
import sys


"""
The purpose of this script is to relaunch sync gateway with the correct config

- It uses cb-bootstrap in order to discover couchbase server IP

"""

# If you are running Sync Gateway, customize your configuration here
sync_gateway_config = """
{
    "log":[
        "HTTP+"
    ],
    "adminInterface":"0.0.0.0:4985",
    "interface":"0.0.0.0:4984",
    "databases":{
        "db":{
            "server":"http://$couchbase_server_ip:8091",
            "bucket":"data-bucket",
            "channel_index":{
                "server":"http://$couchbase_server_ip:8091",
                "bucket":"index-bucket",
                "writer":false
            },
            "users":{
                "GUEST":{
                    "disabled":false,
                    "admin_channels":[
                        "*"
                    ]
                }
            }
        }
    }
}
"""

# If you are running Sync Gateway Acceletor, customize your configuration here
sg_accel_config = """
{
    "log":[
        "HTTP+"
    ],
    "adminInterface":"0.0.0.0:4985",
    "interface":"0.0.0.0:4984",
    "databases":{
        "default":{
            "server":"http://$couchbase_server_ip:8091",
            "bucket":"data-bucket",
            "channel_index":{
                "server":"http://$couchbase_server_ip:8091",
                "bucket":"index-bucket",
                "writer":true
            }
        }
    },
    "cluster_config":{
        "server":"http://$couchbase_server_ip:8091",
        "bucket":"data-bucket",
        "data_dir":"."
    }
}
"""


def relaunch_sg_with_custom_config(stack_name, server_type):

    # Use cbbootrap to call REST API to discover the IP address of the initial couchbase server node
    couchbase_server_ip = cbbootstrap.discover_initial_couchbase_server_ip(stack_name)

    template = Template(sync_gateway_config)
    sync_gateway_config_rendered = template.substitute(couchbase_server_ip=couchbase_server_ip)

    template = Template(sg_accel_config)
    sg_accel_config_rendered = template.substitute(couchbase_server_ip=couchbase_server_ip)

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
    args = parser.parse_args()

    print("{} called with stack name: {}  server type: {}".format(sys.argv[0], args.stack_name, args.server_type))

    relaunch_sg_with_custom_config(args.stack_name, args.server_type)



   
   
