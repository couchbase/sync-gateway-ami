
# Python script to generate an AWS CloudFormation template json file

import collections
from troposphere import Ref, Template, Parameter, Tags, Join, GetAtt, Output
import troposphere.autoscaling as autoscaling
from troposphere.elasticloadbalancing import LoadBalancer
from troposphere import GetAZs
import troposphere.ec2 as ec2
import troposphere.elasticloadbalancing as elb
from troposphere import iam
from troposphere.route53 import RecordSetType
import cloudformation_common as cfncommon

def gen_template(config):

    num_couchbase_servers = config.num_couchbase_servers
    couchbase_instance_type = config.couchbase_instance_type
    sync_gateway_server_type = config.sync_gateway_server_type
    num_load_generators = config.num_load_generators
    load_generator_instance_type = config.load_generator_instance_type

    t = Template()
    t.add_description(
        'An Ec2-classic stack with Sync Gateway + Accelerator + Couchbase Server with horizontally scalable AutoScaleGroup'
    )

    #
    # Parameters
    #
    keyname_param = t.add_parameter(Parameter(
        'KeyName',
        Type='String',
        Description='Name of an existing EC2 KeyPair to enable SSH access',
    ))
    couchbase_server_admin_user_param = t.add_parameter(Parameter(
        'CouchbaseServerAdminUserParam',
        Type='String',
        Description='The Couchbase Server Admin username',
        Default='Administrator',
    ))
    couchbase_server_admin_pass_param = t.add_parameter(Parameter(
        'CouchbaseServerAdminPassParam',
        Type='String',
        Description='The Couchbase Server Admin password',
    ))

    # Security Group
    # ------------------------------------------------------------------------------------------------------------------
    secGrpCouchbase = cfncommon.SecGrpCouchbase(t)


    # EC2 Instance profile + Mobile Testkit Role to allow pushing to CloudWatch Logs
    # ------------------------------------------------------------------------------------------------------------------
    # Create an IAM Role to give the EC2 instance permissions to
    # push Cloudwatch Logs, which avoids the need to bake in the
    # AWS_KEY + AWS_SECRET_KEY into an ~/.aws/credentials file or
    # env variables
    mobileTestKitRole = iam.Role(
        'MobileTestKit',
        ManagedPolicyArns=[
            'arn:aws:iam::aws:policy/CloudWatchFullAccess',
            'arn:aws:iam::aws:policy/AmazonEC2ReadOnlyAccess',
        ],
        AssumeRolePolicyDocument={
            'Version': '2012-10-17',
            'Statement': [{
                'Action': 'sts:AssumeRole',
                'Principal': {'Service': 'ec2.amazonaws.com'},
                'Effect': 'Allow',
            }]
        }
    )
    t.add_resource(mobileTestKitRole)

    # The InstanceProfile instructs the EC2 instance to use
    # the mobileTestKitRole created above.  It will be referenced
    # in the instance.IamInstanceProfile property for all EC2 instances created
    instanceProfile = iam.InstanceProfile(
        'EC2InstanceProfile',
        Roles=[Ref(mobileTestKitRole)],
    )
    t.add_resource(instanceProfile)

    # Couchbase Server Instances
    # ------------------------------------------------------------------------------------------------------------------
    for i in xrange(num_couchbase_servers):
        server_type = "couchbaseserver"
        name = "couchbaseserver{}".format(i)
        instance = ec2.Instance(name)
        instance.ImageId = config.couchbase_ami_id
        instance.InstanceType = couchbase_instance_type
        instance.SecurityGroups = [Ref(secGrpCouchbase)]
        instance.KeyName = Ref(keyname_param)
        instance.Tags = Tags(Name=name, Type=server_type)
        instance.IamInstanceProfile = Ref(instanceProfile)
        instance.UserData = cfncommon.userDataCouchbaseServer(
            Ref(couchbase_server_admin_user_param),
            Ref(couchbase_server_admin_pass_param),
        )
        instance.BlockDeviceMappings = [cfncommon.blockDeviceMapping(config, server_type)]
        t.add_resource(instance)

    # Elastic Load Balancer (ELB)
    # ------------------------------------------------------------------------------------------------------------------
    t.add_resource(cfncommon.SGAutoScaleLoadBalancer)

    # DNS CNAME for Elastic Load Balancer (ELB)
    # ------------------------------------------------------------------------------------------------------------------
    if config.load_balancer_dns_enabled:
        t.add_resource(
            RecordSetType(
                title="SgAutoScaleDNS",
                ResourceRecords=[
                    GetAtt(cfncommon.SGAutoScaleLoadBalancer, "DNSName")
                ],
                TTL="900",
                Name="{}.{}".format(config.load_balancer_dns_hostname, config.load_balancer_dns_hosted_zone_name),
                HostedZoneName=config.load_balancer_dns_hosted_zone_name,
                Type="CNAME",
            )
        )

    # SG LaunchConfiguration (AutoScaleGroup)
    # ------------------------------------------------------------------------------------------------------------------
    SGLaunchConfiguration = autoscaling.LaunchConfiguration(
        "SGLaunchConfiguration",
        ImageId=config.sync_gateway_ami_id,
        KeyName=Ref(keyname_param),
        IamInstanceProfile=Ref(instanceProfile),
        InstanceType=sync_gateway_server_type,
        SecurityGroups=[Ref(secGrpCouchbase)],
        UserData=cfncommon.userDataSyncGateway(),
        BlockDeviceMappings=[cfncommon.blockDeviceMapping(config, "syncgateway")]
    )
    t.add_resource(SGLaunchConfiguration)

    # SG AutoScaleGroup
    # ------------------------------------------------------------------------------------------------------------------
    SGAutoScalingGroup = cfncommon.SGAutoScalingGroup(
        LaunchConfigurationName=Ref(SGLaunchConfiguration),
        LoadBalancerNames=[Ref(cfncommon.SGAutoScaleLoadBalancer)],
    )
    t.add_resource(SGAutoScalingGroup)

    # SG Accel LaunchConfiguration (AutoScaleGroup)
    # ------------------------------------------------------------------------------------------------------------------
    SGAccelLaunchConfiguration = autoscaling.LaunchConfiguration(
        "SGAccelLaunchConfiguration",
        ImageId=config.sg_accel_ami_id,
        KeyName=Ref(keyname_param),
        IamInstanceProfile=Ref(instanceProfile),
        InstanceType=sync_gateway_server_type,
        SecurityGroups=[Ref(secGrpCouchbase)],
        UserData=cfncommon.userDataSGAccel(),
        BlockDeviceMappings=[cfncommon.blockDeviceMapping(config, "sgaccel")]
    )
    t.add_resource(SGAccelLaunchConfiguration)

    # SG Accel AutoScaleGroup
    # ------------------------------------------------------------------------------------------------------------------
    SGAccelAutoScalingGroup = cfncommon.SGAccelAutoScalingGroup(
        LaunchConfigurationName=Ref(SGAccelLaunchConfiguration),
    )
    t.add_resource(SGAccelAutoScalingGroup)

    # Load generator instances
    # ------------------------------------------------------------------------------------------------------------------
    for i in xrange(num_load_generators):
        server_type = "loadgenerator"
        name = "loadgenerator{}".format(i)
        instance = ec2.Instance(name)
        instance.ImageId = config.load_generator_ami_id
        instance.InstanceType = load_generator_instance_type
        instance.SecurityGroups = [Ref(secGrpCouchbase)]
        instance.KeyName = Ref(keyname_param)
        instance.IamInstanceProfile = Ref(instanceProfile)
        instance.UserData = userDataSGAccel()
        instance.Tags = Tags(Name=name, Type=server_type)
        instance.BlockDeviceMappings = [cfncommon.blockDeviceMapping(config, server_type)]

        t.add_resource(instance)

    # Outputs
    # ------------------------------------------------------------------------------------------------------------------
    if config.load_balancer_dns_enabled:
        t.add_output([
            Output(
                "SGAutoScaleLoadBalancerPublicDNS",
                Value=GetAtt(cfncommon.SGAutoScaleLoadBalancer, "DNSName")
            ),
        ])

    return t.to_json()






# Main
# ----------------------------------------------------------------------------------------------------------------------
def main():

    Config = collections.namedtuple(
        'Config',
        " ".join([
            'num_couchbase_servers',
            'couchbase_instance_type',
            'sync_gateway_server_type',
            'num_load_generators',
            'load_generator_instance_type',
            'couchbase_ami_id',
            'sync_gateway_ami_id',
            'sg_accel_ami_id',
            'load_generator_ami_id',
            'load_balancer_dns_enabled',
            'load_balancer_dns_hostname',
            'load_balancer_dns_hosted_zone_name',
            'block_device_name',
            'block_device_volume_size_by_server_type',
            'block_device_volume_type',
        ]),
    )

    region = "us-east-1"  # TODO: make cli parameter

    # Generated via http://uberjenkins.sc.couchbase.com/view/Build/job/couchbase-server-ami/
    couchbase_ami_ids_per_region = {
        "us-east-1": "ami-d8f029ce",
        "us-west-1": "ami-f6b2ec96"
    }

    # Generated via http://uberjenkins.sc.couchbase.com/view/Build/job/sync-gateway-ami/
    sync_gateway_ami_ids_per_region = {
        "us-east-1": "ami-53924045",
        "us-west-1": "ami-f68bd596"
    }

    # Generated via http://uberjenkins.sc.couchbase.com/view/Build/job/sg-accel-ami/
    sg_accel_ami_ids_per_region = {
        "us-east-1": "ami-00914316",
        "us-west-1": "ami-298dd349"
    }

    # Generated via http://uberjenkins.sc.couchbase.com/view/Build/job/sg-load-generator-ami/
    load_generator_ami_ids_per_region = {
        "us-east-1": "ami-3d6ebe2b",
        "us-west-1": "ami-0d8bd56d"
    }

    config = Config(
        num_couchbase_servers=6,
        couchbase_instance_type="c3.2xlarge",
        couchbase_ami_id=couchbase_ami_ids_per_region[region],
        sync_gateway_server_type="c3.2xlarge",
        sync_gateway_ami_id=sync_gateway_ami_ids_per_region[region],
        sg_accel_ami_id=sg_accel_ami_ids_per_region[region],
        num_load_generators=1,
        load_generator_instance_type="c3.2xlarge",
        load_generator_ami_id=load_generator_ami_ids_per_region[region],
        load_balancer_dns_enabled=True,
        load_balancer_dns_hostname="sgautoscale",
        load_balancer_dns_hosted_zone_name="couchbasemobile.com.",
        block_device_name="/dev/sda1",  # "/dev/sda1" for centos, /dev/xvda for amazon linux ami
        block_device_volume_size_by_server_type={"couchbaseserver": 200, "syncgateway": 25, "sgaccel": 25, "loadgenerator": 25},
        block_device_volume_type="gp2",

    )

    templ_json = gen_template(config)

    template_file_name = "generated/sgautoscale_cloudformation_template.json"
    with open(template_file_name, 'w') as f:
        f.write(templ_json)

    print("Wrote cloudformation template: {}".format(template_file_name))


if __name__ == "__main__":
    main()
