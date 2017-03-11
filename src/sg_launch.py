#!/usr/bin/env python

"""

This is "relaunch script" intended to be used for EC2 instances.

It restarts the Sync Gateway or Sync Gateway Accelerator service with
the custom configuration that you provide.

Instructions:

- Customize either the default_sync_gateway_config or the default_sg_accel_config triple quoted string, depending on which type of Sync Gateway you are running.
- Paste the entire contents of this file into the user-data textbox when launching an EC2 instance.

"""

# If you are running Sync Gateway, customize your configuration here
default_sync_gateway_config = """
{
    "log":[
        "HTTP+"
    ],
    "adminInterface":"127.0.0.1:4985",
    "interface":"0.0.0.0:4984",
    "databases":{
        "db":{
            "server":"walrus:data",
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
default_sg_accel_config = """
{
    "log":[
        "HTTP+"
    ],
    "adminInterface":"127.0.0.1:4985",
    "interface":"0.0.0.0:4984",
    "databases":{
        "default":{
            "server":"http://localhost:8091",
            "bucket":"default",
            "channel_index":{
                "server":"http://localhost:8091",
                "bucket":"channel_bucket",
                "writer":true
            }
        }
    },
    "cluster_config":{
        "server":"http://localhost:8091",
        "bucket":"default",
        "data_dir":"."
    }
}
"""

import pwd
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
    
    if sg_server_type is SERVER_TYPE_SYNC_GATEWAY:
        return find_existing_file_in_directories(
            sg_config_candidate_directories,
            "sync_gateway.json"
        )
    elif sg_server_type is SERVER_TYPE_SG_ACCEL:
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
    
    if sg_server_type is SERVER_TYPE_SYNC_GATEWAY:
        config_contents = sync_gateway_config
    elif sg_server_type is SERVER_TYPE_SG_ACCEL:
        config_contents = sg_accel_config
    else:
        raise Exception("Unrecognized server type: {}".format(sg_server_type))

    # Write the file contents to the target config file
    with open(target_config_file, 'w') as f:
        f.write(config_contents)
        
    
def restart_service(sg_server_type):

    binary_name = "Error"
    if sg_server_type is SERVER_TYPE_SYNC_GATEWAY:
        binary_name = "sync_gateway"
    elif sg_server_type is SERVER_TYPE_SG_ACCEL:
        binary_name = "sg_accel"
    else:
        raise Exception("Unrecognized server type: {}".format(sg_server_type))

    cmd = "service {} restart".format(binary_name)

    print("Restarting service: {}".format(cmd))
    
    os.system(cmd)

    
if __name__ == "__main__":

   main(
        default_sync_gateway_config,
        default_sg_accel_config,
        SERVER_TYPE_SYNC_GATEWAY,  # currently this script is only called directly
   )










