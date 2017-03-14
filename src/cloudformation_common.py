
from troposphere import Base64, Join, Ref
import collections
from troposphere import Ref, Template, Parameter, Tags, Join, GetAtt, Output
import troposphere.autoscaling as autoscaling
from troposphere.elasticloadbalancing import LoadBalancer
from troposphere import GetAZs
import troposphere.ec2 as ec2
import troposphere.elasticloadbalancing as elb
from troposphere import iam
from troposphere.route53 import RecordSetType

import sg_launch


# Elastic Load Balancer (ELB)
# ------------------------------------------------------------------------------------------------------------------
def SGAutoScaleLoadBalancer():
    return LoadBalancer(
        "SGAutoScaleLoadBalancer",
        ConnectionDrainingPolicy=elb.ConnectionDrainingPolicy(
            Enabled=True,
            Timeout=120,
        ),
        ConnectionSettings=elb.ConnectionSettings(
            IdleTimeout=3600,  # 1 hour to help avoid 504 GATEWAY_TIMEOUT for continuous changes feeds
        ),
        AvailabilityZones=GetAZs(""),  # Get all AZ's in current region (I think)
        HealthCheck=elb.HealthCheck(
            Target="HTTP:4984/",
            HealthyThreshold="2",
            UnhealthyThreshold="2",
            Interval="5",
            Timeout="3",
        ),
        Listeners=[
            elb.Listener(
                LoadBalancerPort="4984",
                InstancePort="4984",
                Protocol="HTTP",
                InstanceProtocol="HTTP",
            ),
            elb.Listener(
                LoadBalancerPort="4985",
                InstancePort="4985",
                Protocol="HTTP",
                InstanceProtocol="HTTP",
            ),
        ],
        CrossZone=True,
        SecurityGroups=[GetAtt("CouchbaseSecurityGroup", "GroupId")],
        LoadBalancerName=Join('', ["SGAS-", Ref("AWS::StackName")]),
        Scheme="internet-facing",
    )

# SG AutoScaleGroup
# ------------------------------------------------------------------------------------------------------------------
def SGAutoScalingGroup(LaunchConfigurationName, LoadBalancerNames):
    return autoscaling.AutoScalingGroup(
        "SGAutoScalingGroup",
        AvailabilityZones=GetAZs(""),  # Get all AZ's in current region (I think)
        LaunchConfigurationName=LaunchConfigurationName,
        LoadBalancerNames=LoadBalancerNames,
        Tags=[
            autoscaling.Tag(key="Type", value="syncgateway", propogate=True),
            autoscaling.Tag(key="Name", value="syncgateway_autoscale_instance", propogate=True),
        ],
        MaxSize=100,
        MinSize=0,
        DesiredCapacity=1,
    )


# CBServer AutoScalingGroup
# ------------------------------------------------------------------------------------------------------------------
def CBServerAutoScalingGroup(LaunchConfigurationName):
    return autoscaling.AutoScalingGroup(
        "CBServerAutoScalingGroup",
        AvailabilityZones=GetAZs(""),  # Get all AZ's in current region (I think)
        LaunchConfigurationName=LaunchConfigurationName,
        Tags=[
            autoscaling.Tag(key="Type", value="couchbaseserver", propogate=True),
            autoscaling.Tag(key="Name", value="couchbaseserver_autoscale_instance", propogate=True),
        ],
        MaxSize=100,
        MinSize=0,
        DesiredCapacity=1,
    )



def SGAccelAutoScalingGroup(LaunchConfigurationName):
    return autoscaling.AutoScalingGroup(
        "SGAccelAutoScalingGroup",
        AvailabilityZones=GetAZs(""),  # Get all AZ's in current region (I think)
        LaunchConfigurationName=LaunchConfigurationName,
        Tags=[
            autoscaling.Tag(key="Type", value="sgaccel", propogate=True),
            autoscaling.Tag(key="Name", value="sgaccel_autoscale_instance", propogate=True),
        ],
        MaxSize=100,
        MinSize=0,
        DesiredCapacity=1,
    )

def SecGrpCouchbase(t):

    def tcpIngressWithinGroup(name, port, group, groupname):
        return ec2.SecurityGroupIngress(
            name,
            GroupName=Ref(group),
            IpProtocol="tcp",
            FromPort=port,
            ToPort=port,
            SourceSecurityGroupId=GetAtt(groupname, "GroupId"),
        )

    secGrpCouchbase = ec2.SecurityGroup('CouchbaseSecurityGroup')
    secGrpCouchbase.GroupDescription = "External Access to Sync Gateway user port"
    t.add_resource(secGrpCouchbase)

    # Ingress: Public
    # ------------------------------------------------------------------------------------------------------------------
    t.add_resource(ec2.SecurityGroupIngress(
        'IngressSSH',
        GroupName=Ref(secGrpCouchbase),
        IpProtocol="tcp",
        FromPort="22",
        ToPort="22",
        CidrIp="0.0.0.0/0",
    ))
    t.add_resource(ec2.SecurityGroupIngress(
        'IngressSyncGatewayUser',
        GroupName=Ref(secGrpCouchbase),
        IpProtocol="tcp",
        FromPort="4984",
        ToPort="4984",
        CidrIp="0.0.0.0/0",
    ))

    # Ingress: within Security Group
    # ------------------------------------------------------------------------------------------------------------------
    t.add_resource(
        tcpIngressWithinGroup(
            name='IngressCouchbaseErlangPortMapper',
            port="4369",
            group=secGrpCouchbase,
            groupname="CouchbaseSecurityGroup",
        )
    )
    t.add_resource(
        tcpIngressWithinGroup(
            name='IngressSyncGatewayAdmin',
            port="4985",
            group=secGrpCouchbase,
            groupname="CouchbaseSecurityGroup",
        )
    )
    t.add_resource(
        tcpIngressWithinGroup(
            name='IngressCouchbaseWebAdmin',
            port="8091",
            group=secGrpCouchbase,
            groupname="CouchbaseSecurityGroup",
        )
    )
    t.add_resource(
        tcpIngressWithinGroup(
            name='IngressCouchbaseAPI',
            port="8092",
            group=secGrpCouchbase,
            groupname="CouchbaseSecurityGroup",
        )
    )
    t.add_resource(
        tcpIngressWithinGroup(
            name='IngressCouchbaseInternalBucketPort',
            port="11209",
            group=secGrpCouchbase,
            groupname="CouchbaseSecurityGroup",
        )
    )
    t.add_resource(
        tcpIngressWithinGroup(
            name='IngressCouchbaseInternalExternalBucketPort',
            port="11210",
            group=secGrpCouchbase,
            groupname="CouchbaseSecurityGroup",
        )
    )
    t.add_resource(
        tcpIngressWithinGroup(
            name='IngressCouchbaseClientInterfaceProxy',
            port="11211",
            group=secGrpCouchbase,
            groupname="CouchbaseSecurityGroup",
        )
    )
    t.add_resource(
        ec2.SecurityGroupIngress(
            'IngressCouchbaseNodeDataExchange',
            GroupName=Ref(secGrpCouchbase),
            IpProtocol="tcp",
            FromPort="21100",
            ToPort="21299",
            SourceSecurityGroupId=GetAtt("CouchbaseSecurityGroup", "GroupId"),
        )
    )

    return secGrpCouchbase


def blockDeviceMapping(config, server_type):
    return ec2.BlockDeviceMapping(
        DeviceName=config.block_device_name,
        Ebs=ec2.EBSBlockDevice(
            DeleteOnTermination=True,
            VolumeSize=config.block_device_volume_size_by_server_type[server_type],
            VolumeType=config.block_device_volume_type
        )
    )



# Sync Gateway + SG Accel "user data" launch script -- output on ec2 instance available in /var/log/cloud-init-output.log
# ----------------------------------------------------------------------------------------------------------------------
def userDataSyncGateway(sync_gateway_config_url_reference):

    """
    What this script should do:

    - Get passed in a URL where the SG configuration lives, depending on server type (sg, sg accel)
    - Call sg_autoscale_launch.py with config URL, which will
        - Discover Couchbase Server IP addr from cb-bootstrap REST API service
        - Download the config from the URL
        - Extract buckets from the SG config + create buckets (or should that be in cbbootstrap.py?)
        - Replace couchbase server IP placeholder with actual IP
        - Restart Sync Gateway service
    """

    commands = commonCommands() + [
        'python src/sg_autoscale_launch.py --stack-name ', Ref("AWS::StackId"), ' --config-url ', sync_gateway_config_url_reference, ' --server-type ' + sg_launch.SERVER_TYPE_SYNC_GATEWAY + '\n',
    ]
    return Base64(Join('', commands))


def userDataSGAccel(sg_accel_config_url_reference):

    commands = commonCommands() + [
        'python src/sg_autoscale_launch.py --stack-name ', Ref("AWS::StackId"), ' --config-url ', sg_accel_config_url_reference, ' --server-type ' + sg_launch.SERVER_TYPE_SG_ACCEL + '\n',
    ]
    return Base64(Join('', commands))


# Couchbase Server "user data" launch script -- output on ec2 instance available in /var/log/cloud-init-output.log
# ----------------------------------------------------------------------------------------------------------------------
def userDataCouchbaseServer(admin_user_reference, admin_passwword_reference):

    """
    What this script should do:

    - Get passed in a URL where the SG configuration lives
    - Extract buckets from the SG config
    - Create buckets (or .. should that be in sg_autoscale_launch.py?)

    """

    commands = commonCommands() + [
        'sleep 30\n',  # workaround for https://issues.couchbase.com/browse/MB-23081
        'export public_dns_name=$(curl http://169.254.169.254/latest/meta-data/public-hostname)\n',  # call ec2 instance data to get public hostname
        'python src/cbbootstrap.py --cluster-id ', Ref("AWS::StackId"), ' --node-ip-addr-or-hostname ${public_dns_name} --admin-user ',  admin_user_reference, ' --admin-pass ',  admin_passwword_reference, '\n',
    ]
    return Base64(Join('', commands))


# Common "user data" launch script used in all instance types
# ----------------------------------------------------------------------------------------------------------------------
def commonCommands():

    commands = [
        '#!/bin/bash\n',
        'ethtool -K eth0 sg off\n'  # Disable scatter / gather for eth0 (see http://bit.ly/1R25bbE)
        'cd /home/ec2-user/sync-gateway-ami\n',
         # 'git checkout master\n',    # TEMP ONLY.  DON"T CHECK IN.  WOULD BE NEAT TO DO THIS BASED ON AN INSTANCE TAG
         # 'git pull\n',
        'pwd\n',
        'source setup.sh\n',
    ]
    return commands


