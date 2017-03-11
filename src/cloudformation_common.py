
from troposphere import Base64, Join, Ref
import sg_launch

# The "user data" launch script that runs on startup on SG and SG Accel EC2 instances.
# The output from this script is available on the ec2 instance in /var/log/cloud-init-output.log
# ----------------------------------------------------------------------------------------------------------------------
def userDataSGAccel():
    return userDataSyncGatewayOrSgAccel(
        sg_launch.SERVER_TYPE_SG_ACCEL,
    )

# The "user data" launch script that runs on startup on SG and SG Accel EC2 instances.
# The output from this script is available on the ec2 instance in /var/log/cloud-init-output.log
# ----------------------------------------------------------------------------------------------------------------------
def userDataSyncGateway():
    return userDataSyncGatewayOrSgAccel(
        sg_launch.SERVER_TYPE_SYNC_GATEWAY,
    )

def userDataSyncGatewayOrSgAccel(server_type):
    commands = commonCommands() + [
        'python src/sg_autoscale_launch.py --stack-name ', Ref("AWS::StackId"), ' --server-type ' + server_type + '\n',
        # TODO: for sg-autoscale cloudformation, call install_telegraf()
    ]
    return Base64(Join('', commands))

def commonCommands():

    # TODO: Disable transparent hugepages (mainly needed for couchbase server, might as well do everywhere)
    """
    shell: echo 'for i in /sys/kernel/mm/*transparent_hugepage/enabled; do echo never > $i; done' >> /etc/rc.local
    shell: echo 'for i in /sys/kernel/mm/*transparent_hugepage/defrag; do echo never > $i; done' >> /etc/rc.local
    shell: for i in /sys/kernel/mm/*transparent_hugepage/enabled; do echo never > $i; done
    """
    commands = [
        '#!/bin/bash\n',
        'ethtool -K eth0 sg off\n'  # Disable scatter / gather for eth0 (see http://bit.ly/1R25bbE)
        'cd /home/ec2-user/sync-gateway-ami\n',
        'pwd\n',
        'source setup.sh\n',
    ]
    return commands


# The "user data" launch script that runs on startup on Couchbase Server instances
# The output from this script is available on the ec2 instance in /var/log/cloud-init-output.log
# ----------------------------------------------------------------------------------------------------------------------
def userDataCouchbaseServer(admin_user_reference, admin_passwword_reference):

    commands = commonCommands() + [
        'export public_dns_name=$(curl http://169.254.169.254/latest/meta-data/public-hostname)\n',  # call ec2 instance data to get public hostname
        'python cbbootstrap.py --cluster-id ', Ref("AWS::StackId"), ' --node-ip-addr-or-hostname ${public_dns_name} --admin-user ',  admin_user_reference, ' --admin-pass ',  admin_passwword_reference, '\n',
        # TODO: for sg-autoscale cloudformation, call install_telegraf()
    ]
    return Base64(Join('', commands))


