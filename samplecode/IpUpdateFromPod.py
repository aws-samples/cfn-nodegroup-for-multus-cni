## This is an example code to show how we can assign service IP address to multus interface from the Pod.
## For this Pod should be with net_admin priviledge.

import requests
import boto3, json
import sys
from requests.packages.urllib3 import Retry

ec2_client = boto3.client('ec2', region_name='us-west-2')

def assign_ip():
    instance_id = get_instance_id()
    subnet_cidr = "10.0.100.0/24"

    response = ec2_client.describe_subnets(
        Filters=[
            {
                'Name': 'cidr-block',
                'Values': [
                    subnet_cidr,
                ]
            },
        ]
    )

    for i in response['Subnets']:
        subnet_id = i['SubnetId']
        break

    response = ec2_client.describe_network_interfaces(
        Filters=[
            {
                'Name': 'subnet-id',
                'Values': [
                    subnet_id,
                ]
            },
            {
                'Name': 'attachment.instance-id',
                'Values': [
                    instance_id,
                ]
            }
        ]
    )

    for j in response['NetworkInterfaces']:
        network_interface_id = j['NetworkInterfaceId']
        break

    response = ec2_client.assign_private_ip_addresses(
        AllowReassignment=True,
        NetworkInterfaceId=network_interface_id,
        PrivateIpAddresses=[
            "10.0.100.70",
        ]
    )

def get_instance_id():
    instance_identity_url = "http://169.254.169.254/latest/dynamic/instance-identity/document"
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=0.3)
    metadata_adapter = requests.adapters.HTTPAdapter(max_retries=retries)
    session.mount("http://169.254.169.254/", metadata_adapter)
    try:
        r = requests.get(instance_identity_url, timeout=(2, 5))
    except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError) as err:
        print("Connection to AWS EC2 Metadata timed out: " + str(err.__class__.__name__))
        print("Is this an EC2 instance? Is the AWS metadata endpoint blocked? (http://169.254.169.254/)")
        sys.exit(1)
    response_json = r.json()
    instanceid = response_json.get("instanceId")
    return(instanceid)

assign_ip()
