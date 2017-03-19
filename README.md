
This repo contains scripts to:

- Build Sync Gateway AMI's
- Launch Couchbase Server + Sync Gateway AMI's in Cloudformation

This README is meant for developers that need to produce and deploy packaged AMI's to AWS.  If you just want to **consume** an AMI or launch a Cloudformation, see [README-ENDUSER.md](docs/README-ENDUSER.md)

## End-user documentation

See [README-ENDUSER.md](docs/README-ENDUSER.md)

## Activate virtualenv

```
$ source setup.sh
```

## Generate cloudformation templates

```
$ python src/cloudformation_template.py
```

You should have an updated file in `generated/generated_cloudformation_template.json`

## Launch Cloudformation via CLI

Here is a sample Cloudformation CLI command to launch.

**Be sure to replace all YOUR_* example values with valid values, in particular YOUR_PASSWORD**

```
$ aws cloudformation create-stack --stack-name YOUR_STACK_NAME \
  --template-body file://generated/generated_cloudformation_template.json
  --region us-east-1
  --parameters ParameterKey=KeyName,ParameterValue=YOUR_KEY_NAME \
               ParameterKey=CouchbaseServerAdminPassword,ParameterValue=YOUR_PASSWORD

```

## Deploy updated Cloudformation

Upload to s3:

```
http://cbmobile-cloudformation-templates.s3.amazonaws.com/SyncGateway1.4.0/generated_cloudformation_template.json
```

## Jenkins Automation Jobs

* [sync-gateway-ami](http://uberjenkins.sc.couchbase.com/view/Build/job/sync-gateway-ami/) 
* [sg-accel-ami](http://uberjenkins.sc.couchbase.com/view/Build/job/sg-accel-ami/)



