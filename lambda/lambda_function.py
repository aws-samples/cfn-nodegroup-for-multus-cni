import boto3
import botocore
import os,sys
from datetime import datetime

ec2_client = boto3.client('ec2')
asg_client = boto3.client('autoscaling')
ec2 = boto3.resource('ec2')

def lambda_handler(event, context):
    instance_id = event['detail']['EC2InstanceId']
    LifecycleHookName=event['detail']['LifecycleHookName']
    AutoScalingGroupName=event['detail']['AutoScalingGroupName']

    if os.environ['SecGroupIds'] :
        secgroup_ids = os.environ['SecGroupIds'].split(",")
    else:
        log("Empty Environment variable SecGroupIds:"+ os.environ['SecGroupIds'])
        exit (1)
    if os.environ['SubnetIds'] :
        subnet_ids = os.environ['SubnetIds'].split(",")
    else:
        log("Empty Environment variable SubnetIds:"+ os.environ['SubnetIds'])
        exit (1)
    log("subnet-ids:"+str(subnet_ids))
    log("secgroup-ids:" + str(secgroup_ids))
    #if only 1 securitygroup is passed then use the same secgroup with all multus, fill the array
    if len(secgroup_ids) != len(subnet_ids):
        if len(secgroup_ids) == 1:
            index=1
            while index < len(subnet_ids) :
                secgroup_ids.append(secgroup_ids[index-1])
                index = index +1
        else:
            log("length of SecGroupIds :"+ len(secgroup_ids)  + "  not same as length of subnets "+ len(subnet_ids) )
            exit (1)


    if event["detail-type"] == "EC2 Instance-launch Lifecycle Action":
        index = 1
        for x in subnet_ids:
            interface_id = create_interface(x,secgroup_ids[index-1])
            attachment = attach_interface(interface_id,instance_id,index)
            index = index+1
            if not interface_id:
                complete_lifecycle_action_failure(LifecycleHookName,AutoScalingGroupName,instance_id)
                return
            elif not attachment:
                complete_lifecycle_action_failure(LifecycleHookName,AutoScalingGroupName,instance_id)
                delete_interface(interface_id)
                return
        complete_lifecycle_action_success(LifecycleHookName,AutoScalingGroupName,instance_id)

    if event["detail-type"] == "EC2 Instance-terminate Lifecycle Action":
        interface_ids = []
        attachment_ids = []

        # -* K8s draining function should be added here -*#

        complete_lifecycle_action_success(LifecycleHookName,AutoScalingGroupName,instance_id)

def isIPv6(subnet_id):
    ipv6=False

    try:
        response = ec2_client.describe_subnets(
            SubnetIds=[
                subnet_id,
            ],
        )

        for i in response['Subnets']:
           if i['Ipv6CidrBlockAssociationSet']:
                ipv6=True
    except botocore.exceptions.ClientError as e:
        log("Error describing subnet : {}".format(e.response['Error']))
    return ipv6

def create_interface(subnet_id,sg_id):
    network_interface_id = None
    print("create_interface subnet:" + subnet_id +" secgroup:" + sg_id)
    log("create_interface: {}".format(network_interface_id))

    if subnet_id:
        try:
            if isIPv6(subnet_id) == True:
                network_interface = ec2_client.create_network_interface(Groups=[sg_id],SubnetId=subnet_id, Ipv6AddressCount=1)
            else :
                network_interface = ec2_client.create_network_interface(Groups=[sg_id],SubnetId=subnet_id)
            network_interface_id = network_interface['NetworkInterface']['NetworkInterfaceId']
            log("Created network interface: {}".format(network_interface_id))
        except botocore.exceptions.ClientError as e:
            log("Error creating network interface: {}".format(e.response['Error']))
    return network_interface_id


def attach_interface(network_interface_id, instance_id, index):
    # Tag creation first before attachment for compatibility to VPC CNI 1.7.5
    network_interface = ec2.NetworkInterface(network_interface_id)
    network_interface.create_tags(
        Tags=[
                {
                    'Key': 'node.k8s.amazonaws.com/no_manage',
                    'Value': 'true'
            }
        ]
    )

    attachment = None
    if network_interface_id and instance_id:
        try:
            attach_interface = ec2_client.attach_network_interface(
                NetworkInterfaceId=network_interface_id,
                InstanceId=instance_id,
                DeviceIndex=index
            )
            attachment = attach_interface['AttachmentId']
            log("Created network attachment: {}".format(attachment))
        except botocore.exceptions.ClientError as e:
            log("Error attaching network interface: {}".format(e.response['Error']))

    #modify_attribute doesn't allow multiple parameter change at once..
    network_interface.modify_attribute(
        SourceDestCheck={
            'Value': False
        }
    )
    network_interface.modify_attribute(
        Attachment={
            'AttachmentId': attachment,
            'DeleteOnTermination': True
        },
    )

    return attachment


def delete_interface(network_interface_id):
    try:
        ec2_client.delete_network_interface(
            NetworkInterfaceId=network_interface_id
        )
        log("Deleted network interface: {}".format(network_interface_id))
        return True

    except botocore.exceptions.ClientError as e:
        log("Error deleting interface {}: {}".format(network_interface_id,e.response['Error']))


def complete_lifecycle_action_success(hookname,groupname,instance_id):
    try:
        asg_client.complete_lifecycle_action(
            LifecycleHookName=hookname,
            AutoScalingGroupName=groupname,
            InstanceId=instance_id,
            LifecycleActionResult='CONTINUE'
        )
        log("Lifecycle hook CONTINUEd for: {}".format(instance_id))
    except botocore.exceptions.ClientError as e:
            log("Error completing life cycle hook for instance {}: {}".format(instance_id, e.response['Error']))
            log('{"Error": "1"}')

def complete_lifecycle_action_failure(hookname,groupname,instance_id):
    try:
        asg_client.complete_lifecycle_action(
            LifecycleHookName=hookname,
            AutoScalingGroupName=groupname,
            InstanceId=instance_id,
            LifecycleActionResult='ABANDON'
        )
        log("Lifecycle hook ABANDONed for: {}".format(instance_id))
    except botocore.exceptions.ClientError as e:
            log("Error completing life cycle hook for instance {}: {}".format(instance_id, e.response['Error']))
            log('{"Error": "1"}')

def log(error):
    print('{}Z {}'.format(datetime.utcnow().isoformat(), error))
