#!/usr/bin/env python

"""

This is "relaunch script" intended to be used for EC2 instances.

It restarts the Sync Gateway or Sync Gateway Accelerator service with
the custom configuration that you provide.

NOTE: currently just library code used from sg_autoscale_launch.py

"""

import os
import time
import urllib2

SERVER_TYPE_SYNC_GATEWAY = "sg"
SERVER_TYPE_SG_ACCEL = "sg-accel"
SERVER_TYPE_LOAD_GEN = "SERVER_TYPE_LOAD_GEN"
SERVER_TYPE_COUCHBASE_SERVER = "SERVER_TYPE_COUCHBASE_SERVER"


def main(sync_gateway_config, sg_accel_config, server_type):

    target_config_file = discover_target_config(server_type)

    write_custom_config(
        server_type,
        target_config_file,
        sync_gateway_config,
        sg_accel_config,
    )

    for i in range(30):

        restart_service(server_type)

        time.sleep(5)  # Give it a few seconds to bind to port

        if is_service_running(server_type):
            # the service is running, we're done
            print("Service is running.  Finished.")
            return

        print("Service not up yet, sleeping {} seconds and retrying".format(i)) 
        time.sleep(i)


def discover_target_config(sg_server_type):

    sg_config_candidate_directories = [
        "/opt/sync_gateway/etc",
        "/home/sync_gateway",
    ]
    sg_accel_config_candidate_directories = [
        "/opt/sg_accel/etc",
        "/home/sg_accel",
    ]
    
    if sg_server_type == SERVER_TYPE_SYNC_GATEWAY:
        return find_existing_file_in_directories(
            sg_config_candidate_directories,
            "sync_gateway.json"
        )
    elif sg_server_type == SERVER_TYPE_SG_ACCEL:
        return find_existing_file_in_directories(
            sg_accel_config_candidate_directories,
            "sg_accel.json"
        )
    else:
        raise Exception("Unrecognized server type: {}".format(sg_server_type))

def is_service_running(sg_server_type):

    try:
        
        contents = urllib2.urlopen("http://localhost:4985").read()
        if "Couchbase" in contents:
            return True
        return False

    except Exception as e:
        return False

    
def find_existing_file_in_directories(directories, filename):
    
    for dir in directories:
        path_to_file = os.path.join(dir, filename)
        if os.path.exists(path_to_file):
            return path_to_file
    raise Exception("Did not find {} in {}".format(filename, directories))
        

    
def write_custom_config(sg_server_type, target_config_file, sync_gateway_config, sg_accel_config):
    
    config_contents = "Error"
    
    if sg_server_type == SERVER_TYPE_SYNC_GATEWAY:
        config_contents = sync_gateway_config
    elif sg_server_type == SERVER_TYPE_SG_ACCEL:
        config_contents = sg_accel_config
    else:
        raise Exception("Unrecognized server type: {}".format(sg_server_type))

    # Write the file contents to the target config file
    with open(target_config_file, 'w') as f:
        f.write(config_contents)
        
    
def restart_service(sg_server_type):

    binary_name = "Error"
    if sg_server_type == SERVER_TYPE_SYNC_GATEWAY:
        binary_name = "sync_gateway"
    elif sg_server_type == SERVER_TYPE_SG_ACCEL:
        binary_name = "sg_accel"
    else:
        raise Exception("Unrecognized server type: {}".format(sg_server_type))

    cmd = "service {} restart".format(binary_name)

    print("Restarting service: {}".format(cmd))
    
    os.system(cmd)












