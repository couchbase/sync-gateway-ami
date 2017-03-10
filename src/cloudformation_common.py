
from troposphere import Base64, Join


# The "user data" launch script that runs on startup on SG and SG Accel EC2 instances.
# The output from this script is available on the ec2 instance in /var/log/cloud-init-output.log
# ----------------------------------------------------------------------------------------------------------------------
def userDataSGAccel(build_repo_commit, sgautoscale_repo_commit):
    return Base64(Join('', [
        '#!/bin/bash\n',
        'cd $HOME\n',
        'pwd\n',
        
        'export PYTHONPATH=.',
        'python sg_autoscale_launch.py --stack-name ', Ref("AWS::StackId"), '\n',
        'ethtool -K eth0 sg off\n'  # Disable scatter / gather for eth0 (see http://bit.ly/1R25bbE)
    ]))

# The "user data" launch script that runs on startup on SG and SG Accel EC2 instances.
# The output from this script is available on the ec2 instance in /var/log/cloud-init-output.log
# ----------------------------------------------------------------------------------------------------------------------
def userDataSyncGateway(build_repo_commit, sgautoscale_repo_commit):
    return Base64(Join('', [
        '#!/bin/bash\n',
        'cd /path/to/where/I/git/cloned',
        'export PYTHONPATH=.',
        'python sg_autoscale_launch.py --stack-name ', Ref("AWS::StackId"), '--server-type', '\n',
        'ethtool -K eth0 sg off\n'  # Disable scatter / gather for eth0 (see http://bit.ly/1R25bbE)
    ]))

# The "user data" launch script that runs on startup on Couchbase Server instances
# The output from this script is available on the ec2 instance in /var/log/cloud-init-output.log
# ----------------------------------------------------------------------------------------------------------------------
def userDataCouchbaseServer(build_repo_commit, sgautoscale_repo_commit, admin_user_reference, admin_passwword_reference):

    # TODO
    """
    shell: echo 'for i in /sys/kernel/mm/*transparent_hugepage/enabled; do echo never > $i; done' >> /etc/rc.local
    shell: echo 'for i in /sys/kernel/mm/*transparent_hugepage/defrag; do echo never > $i; done' >> /etc/rc.local
    shell: for i in /sys/kernel/mm/*transparent_hugepage/enabled; do echo never > $i; done
    """

    return Base64(Join('', [
        '#!/bin/bash\n',
        'service couchbase-server status\n',
        'sleep 60\n',  # workaround for https://issues.couchbase.com/browse/MB-23081
        'service couchbase-server status\n',
        'cd /path/to/where/I/git/cloned',
        'export PYTHONPATH=.',
        'python sg_autoscale_launch.py --stack-name ', Ref("AWS::StackId"), '\n',  # on couchbase server machines, only installs telegraf.
        'export public_dns_name=$(curl http://169.254.169.254/latest/meta-data/public-hostname)\n',  # call ec2 instance data to get public hostname
        'python cbbootstrap.py --cluster-id ', Ref("AWS::StackId"), ' --node-ip-addr-or-hostname ${public_dns_name} --admin-user ',  admin_user_reference, ' --admin-pass ',  admin_passwword_reference, '\n',
        'ethtool -K eth0 sg off\n'  # Disable scatter / gather for eth0 (see http://bit.ly/1R25bbE)
    ]))

