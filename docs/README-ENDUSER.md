
Running the Couchbase Mobile Sync Gateway / Sync Gateway Accelerator AMI

## AMI Overview

The following AMI's are available on the AWS Marketplace:

1. Sync Gateway 1.4 Community Edition
1. Sync Gateway 1.4 Enterprise Edition
1. Sync Gateway Accelerator 1.4 Enterprise Edition

## Launch Sync Gateway EC2 Instance with an in-memory backing store

* Choose Sync Gateway 1.4 Community or Enterprise Edition AMI with the appropriate region
* Edit your Security Group to expose port 4984 to Anywhere
* Launch instance

### Verify

* In the AWS Management Console web UI, go to the **EC2** section and look for an instance named `syncgateway`, and click it to show the instance details
* Find the public dns name of the instance from the **Public DNS (IPv4)** field: it should look something like **ec2-54-152-154-24.compute-1.amazonaws.com**
* In your browser, go to port 4984 **http://public-dns-name-of-instance:4984** and it should return JSON content like `{couchdb: "Welcome", ..etc ..`

### Customize Sync Gateway configuration

If you need to customize the Sync Gateway configuration, find the hostname of the Sync Gateway EC2 instance and:

```
$ ssh ec2-user@hostname
```

Update the configuration:

```
$ sudo bash
$ vi /opt/sync_gateway/etc/sync_gateway.json
```

Restart the Sync Gateway service:

```
$ service sync_gateway restart
```

## Launch CloudFormation with: Sync Gateways + Sync Gateway Accelerators + Couchbase Servers

To launch a full mobile backend Cloudformation stack click the **Launch Stack** button below:

[![Launch CouchbaseSyncGateway](https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png)](https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/new?stackName=CouchbaseSyncGateway&templateURL=http://cbmobile-cloudformation-templates.s3.amazonaws.com/SyncGateway1.4.0/generated_cloudformation_template.json)

You will need to customize:

1. The Couchbase Server Admin password -- please use something that is hard to guess
1. The SSH key name which allows you to SSH into any of the instances.  If you don't already have one registered in EC2, you will need to add one.

This will create the following EC2 instances:

- Couchbase Server Enterprise Edition 4.5.0
- Sync Gateway 1.4 Enterprise Edition
- Sync Gateway Accel 1.4 Enterprise Edition


### Connect to Couchbase Web Admin

By default, the Couchbase Web Admin port 8091 is not accessible.

**Allow restricted access to port 8091**

1. In the AWS EC2 Web Console instance list, click the `couchbaseserver` instance
1. Under **Security Groups**, click the security group
1. Choose the **Inbound** tab
1. Click the **Edit** button
1. Add a new rule with
       * **Type** Custom TCP Rule
       * **Protocol** TCP
       * **Port Range** 8091
       * **Source** Find your external IP address (you may need to ask your network administrator), and if your IP is `173.228.112.82` use `173.228.112.82/32`

**Login to Couchbase Server**

1. In the AWS Management Console web UI, find a Couchbase Server instance from the CouchbaseServer AutoScalingGroup you just launched, and click it to show the instance details
1. Find the public dns name of the instance from the **Public DNS (IPv4)** field: it should look something like **ec2-54-152-154-24.compute-1.amazonaws.com**
1. In your browser, go to port 4984 **http://public-dns-name-of-instance:8091** and it should show a login screen.  Use the Username/Password combo that you used when launching the Cloudformation.


