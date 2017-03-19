
# Python script to generate an AWS CloudFormation template json file

import collections
from troposphere import Ref, Template, Parameter, Tags, Base64, Join, GetAtt, Output
import troposphere.autoscaling as autoscaling
import cloudformation_common as cfncommon

def gen_template(config):

    t = Template()
    t.add_description(
        'Sync Gateway + Sync Gateway Accelerator + Couchbase Server'
    )
    
    #
    # Template Parameters
    #
    keyname_param = t.add_parameter(Parameter(
        'KeyName',
        Type='String',
        Description='Name of an existing EC2 KeyPair to enable SSH access',
        MinLength=1,
    ))
    couchbase_server_instance_type_param = t.add_parameter(Parameter(
        'CouchbaseServerInstanceType',
        Type='String',
        Description='The InstanceType to use for Couchbase Server instance',
        Default='m3.medium',
    ))
    sync_gateway_instance_type_param = t.add_parameter(Parameter(
        'SyncGatewayInstanceType',
        Type='String',
        Description='The InstanceType to use for Sync Gateway instance',
        Default='m3.medium',
    ))
    sg_accel_instance_type_param = t.add_parameter(Parameter(
        'SgAccelInstanceType',
        Type='String',
        Description='The InstanceType to use for Sync Gateway Accel instance',
        Default='m3.medium',
    ))
    sync_gateway_config_url_param = t.add_parameter(Parameter(
        'SyncGatewayConfigUrl',
        Type='String',
        Description='URL which contains Sync Gateway configuration template',
        Default='http://cbmobile-aws.s3.amazonaws.com/cloudformation-sync-gateway-config/SyncGateway1.4.0/sync_gateway.json.template',
    ))
    sg_accel_config_url_param = t.add_parameter(Parameter(
        'SgAccelConfigUrl',
        Type='String',
        Description='URL which contains Sync Gateway Accelerator configuration template',
        Default='http://cbmobile-aws.s3.amazonaws.com/cloudformation-sync-gateway-config/SyncGateway1.4.0/sg_accel.json.template',
    ))
    couchbase_server_admin_user_param = t.add_parameter(Parameter(
        'CouchbaseServerAdminUser',
        Type='String',
        Description='The Couchbase Server Admin username',
        Default='Administrator',
    ))
    couchbase_server_admin_pass_param = t.add_parameter(Parameter(
        'CouchbaseServerAdminPassword',
        Type='String',
        Description='The Couchbase Server Admin password',
        MinLength=8,
        NoEcho=True,
    ))

    # The user must pass in the AvailabilityZone to use, see: http://stackoverflow.com/questions/41903166/create-failed-elasticloadbalancerthe-requested-availability-zone-us-east-1c-is
    # Without this, was getting the following errors in *some* AWS accounts: https://gist.github.com/tleyden/b18f9b4d8be094954c9bb009b1b4e5ca
    availability_zone_parameter = t.add_parameter(Parameter(
        'AvailabilityZone',
        Type='AWS::EC2::AvailabilityZone::Name',
        Description='The availability zone param.  Workaround for http://stackoverflow.com/questions/41903166/create-failed-elasticloadbalancerthe-requested-availability-zone-us-east-1c-is',
        Default='us-east-1a',
    ))

    # Security Group
    # ------------------------------------------------------------------------------------------------------------------
    secGrpCouchbase = cfncommon.SecGrpCouchbase(t)

    # Load Balancer
    # ------------------------------------------------------------------------------------------------------------------
    SGAutoScaleLoadBalancer = cfncommon.SGAutoScaleLoadBalancer(
        AvailabilityZoneReference=Ref(availability_zone_parameter),
    )
    t.add_resource(SGAutoScaleLoadBalancer)

    # Couchbase Server LaunchConfiguration (AutoScaleGroup)
    # ------------------------------------------------------------------------------------------------------------------
    CBServerLaunchConfiguration = autoscaling.LaunchConfiguration(
        "CBServerLaunchConfiguration",
        ImageId=config.couchbase_ami_id,
        KeyName=Ref(keyname_param),
        InstanceType=Ref(couchbase_server_instance_type_param),
        SecurityGroups=[Ref(secGrpCouchbase)],
        UserData=cfncommon.userDataCouchbaseServer(
            Ref(couchbase_server_admin_user_param),
            Ref(couchbase_server_admin_pass_param),
        ),
        BlockDeviceMappings=[cfncommon.blockDeviceMapping(config, "couchbaseserver")]
    )
    t.add_resource(CBServerLaunchConfiguration)

    # CB Server AutoScaleGroup
    # ------------------------------------------------------------------------------------------------------------------
    CBServerAutoScalingGroup = cfncommon.CBServerAutoScalingGroup(
        LaunchConfigurationName=Ref(CBServerLaunchConfiguration),
        AvailabilityZoneReference=Ref(availability_zone_parameter),
    )
    t.add_resource(CBServerAutoScalingGroup)


    # SG LaunchConfiguration (AutoScaleGroup)
    # ------------------------------------------------------------------------------------------------------------------
    SGLaunchConfiguration = autoscaling.LaunchConfiguration(
        "SGLaunchConfiguration",
        ImageId=config.sync_gateway_ami_id,
        KeyName=Ref(keyname_param),
        InstanceType=Ref(sync_gateway_instance_type_param),
        SecurityGroups=[Ref(secGrpCouchbase)],
        UserData=cfncommon.userDataSyncGateway(Ref(sync_gateway_config_url_param)),
        BlockDeviceMappings=[cfncommon.blockDeviceMapping(config, "syncgateway")]
    )
    t.add_resource(SGLaunchConfiguration)

    # SG AutoScaleGroup
    # ------------------------------------------------------------------------------------------------------------------
    SGAutoScalingGroup = cfncommon.SGAutoScalingGroup(
        LaunchConfigurationName=Ref(SGLaunchConfiguration),
        LoadBalancerNames=[Ref(SGAutoScaleLoadBalancer)],
        AvailabilityZoneReference=Ref(availability_zone_parameter),
    )
    t.add_resource(SGAutoScalingGroup)

    # SG Accel LaunchConfiguration (AutoScaleGroup)
    # ------------------------------------------------------------------------------------------------------------------
    SGAccelLaunchConfiguration = autoscaling.LaunchConfiguration(
        "SGAccelLaunchConfiguration",
        ImageId=config.sg_accel_ami_id,
        KeyName=Ref(keyname_param),
        InstanceType=Ref(sg_accel_instance_type_param),
        SecurityGroups=[Ref(secGrpCouchbase)],
        UserData=cfncommon.userDataSGAccel(Ref(sg_accel_config_url_param)),
        BlockDeviceMappings=[cfncommon.blockDeviceMapping(config, "sgaccel")]
    )
    t.add_resource(SGAccelLaunchConfiguration)

    # SG Accel AutoScaleGroup
    # ------------------------------------------------------------------------------------------------------------------
    SGAccelAutoScalingGroup = cfncommon.SGAccelAutoScalingGroup(
        LaunchConfigurationName=Ref(SGAccelLaunchConfiguration),
        AvailabilityZoneReference=Ref(availability_zone_parameter),
    )
    t.add_resource(SGAccelAutoScalingGroup)

    return t.to_json()


# Main
# ----------------------------------------------------------------------------------------------------------------------
def main():

    Config = collections.namedtuple(
        'Config',
        " ".join([
            'couchbase_ami_id',
            'sync_gateway_ami_id',
            'sg_accel_ami_id',
            'block_device_name',
            'block_device_volume_size_by_server_type',
            'block_device_volume_type',
        ]),
    )

    region = "us-east-1"  # TODO: make cli parameter

    # TODO: should it query AMI's by name and owner instead?

    # Generated via http://uberjenkins.sc.couchbase.com/view/Build/job/couchbase-server-ami/
    couchbase_ami_ids_per_region = {
        "us-east-1": "ami-2eeb4538",
        "us-west-1": "ami-d45c05b4"
    }

    # Generated via http://uberjenkins.sc.couchbase.com/view/Build/job/sync-gateway-ami/
    sync_gateway_ami_ids_per_region = {
        "us-east-1": "ami-b76bc5a1",
        "us-west-1": "ami-4cf0ae2c"
    }

    # Generated via http://uberjenkins.sc.couchbase.com/view/Build/job/sg-accel-ami/
    sg_accel_ami_ids_per_region = {
        "us-east-1": "ami-dc69c7ca",
        "us-west-1": "ami-9a267ffa"
    }

    config = Config(
        couchbase_ami_id=couchbase_ami_ids_per_region[region],
        sync_gateway_ami_id=sync_gateway_ami_ids_per_region[region],
        sg_accel_ami_id=sg_accel_ami_ids_per_region[region],
        block_device_name="/dev/xvda",  # "/dev/sda1" for centos, /dev/xvda for amazon linux ami
        block_device_volume_size_by_server_type={"couchbaseserver": 200, "syncgateway": 25, "sgaccel": 25},
        block_device_volume_type="gp2",
    )

    templ_json = gen_template(config)

    template_file_name = "generated/generated_cloudformation_template.json"
    with open(template_file_name, 'w') as f:
        f.write(templ_json)

    print("Wrote cloudformation template: {}".format(template_file_name))


if __name__ == "__main__":
    main()
