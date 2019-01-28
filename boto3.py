import boto3
import time
import json

ec2 = boto3.resource('ec2', aws_access_key_id='yourkey',
                     aws_secret_access_key='yourkey',
                     region_name='us-east-1')

client = boto3.client('iam')

#create iam role

profile = client.create_instance_profile(
   InstanceProfileName='ec2-profile',
)

assume_role_policy_document = json.dumps({
    "Version": "2012-10-17",
    "Statement": [
        {
        "Effect": "Allow",
        "Principal": {
            "Service": "ec2.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
        }
    ]
})

create_role_response = client.create_role(
    RoleName = "ec2-role",
    AssumeRolePolicyDocument = assume_role_policy_document
)

role_profile = client.add_role_to_instance_profile(
   InstanceProfileName=profile['InstanceProfile']['InstanceProfileName'],
   RoleName=create_role_response['Role']['RoleName']
)


#create policy

PolicyDocument1 = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": "ec2:*",
            "Resource": "*"
        }
    ]
}


response = client.create_policy(
    PolicyName = "ec2-access",
    PolicyDocument = json.dumps(PolicyDocument1)
)

print(response['Policy']['PolicyName'])

# attach policy to role

attach_policy = client.attach_role_policy(
    RoleName=create_role_response['Role']['RoleName'],
    PolicyArn=response['Policy']['Arn']
)


client=boto3.client('ec2')

# create VPC
ec2 = boto3.resource('ec2')
vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16', AmazonProvidedIpv6CidrBlock=True)

print(vpc.id)

# create and attach internet gateway
ig = ec2.create_internet_gateway()
vpc.attach_internet_gateway(InternetGatewayId=ig.id)
print(ig.id)

# create a route table and a public route
route_table = vpc.create_route_table()
route = route_table.create_route(DestinationCidrBlock='0.0.0.0/0',GatewayId=ig.id)
print(route_table.id)


# create subnet
subnet_public = ec2.create_subnet(CidrBlock='10.0.0.0/24', VpcId=vpc.id)
print(subnet_public.id)

# create subnet
subnet_public2 = ec2.create_subnet(CidrBlock='10.0.2.0/24', VpcId=vpc.id, AvailabilityZone ='us-east-1b')
print(subnet_public2.id)

# create Private subnet
subnet_private = ec2.create_subnet(CidrBlock='10.0.1.0/24', VpcId=vpc.id)
print(subnet_private.id)


elastic_ip = client.allocate_address(Domain='vpc')
print(elastic_ip['AllocationId'])

# create nat gateway
nat_gateway = client.create_nat_gateway(AllocationId=elastic_ip['AllocationId'], SubnetId=subnet_public.id)
print(nat_gateway['NatGateway']['NatGatewayId'])
time.sleep(20)

# create a route table and a private route
route_table_private = vpc.create_route_table()
route = route_table_private.create_route(DestinationCidrBlock='0.0.0.0/0',NatGatewayId=nat_gateway['NatGateway']['NatGatewayId'])
print(route_table_private.id)

# associate the route table with the subnets
route_table.associate_with_subnet(SubnetId=subnet_public.id)
route_table.associate_with_subnet(SubnetId=subnet_public2.id)

route_table_private.associate_with_subnet(SubnetId=subnet_private.id)


# Create sec group for instance
sec_group = ec2.create_security_group(
    GroupName='test_0', Description='test_0 sec group', VpcId=vpc.id)
sec_group.authorize_ingress(
    CidrIp='0.0.0.0/0',
    IpProtocol='tcp',
    FromPort=22,
    ToPort=22
)
sec_group.authorize_ingress(
    CidrIp='0.0.0.0/0',
    IpProtocol='tcp',
    FromPort=80,
    ToPort=80
)
print(sec_group.id)

ec2 = boto3.resource('ec2', region_name='us-east-1')

#Enhanced creation now with the addition of 'user_data'

user_data_script = """#!/bin/bash
sudo yum install httpd -y
sudo yum update -y
sudo touch /var/www/html/index.html
sudo echo "Welcome to Homepage" > /var/www/html/index.html
sudo service httpd start
sudo chkconfig httpd on"""


instances = ec2.create_instances(ImageId='ami-035be7bafff33b6b6', MinCount=1, MaxCount=1, InstanceType='t2.micro', IamInstanceProfile={ 'Name' :profile['InstanceProfile']['InstanceProfileName'] }, KeyName='ec2-keypair', SecurityGroupIds=[sec_group.id], Placement={ 'AvailabilityZone': subnet_private.availability_zone }, SubnetId=subnet_private.id, UserData=user_data_script )
instances[0].wait_until_running()
print(instances[0].id)

# Create sec group
sec_group_lb = ec2.create_security_group(
    GroupName='load_0', Description='load_0 sec group', VpcId=vpc.id)
sec_group_lb.authorize_ingress(
    CidrIp='0.0.0.0/0',
    IpProtocol='tcp',
    FromPort=0,
    ToPort=6535
)

print(sec_group_lb.id)

#create load balancer
client = boto3.client('elb')

load_balancer = client.create_load_balancer(LoadBalancerName='test-load-balancer', Listeners=[{ 'Protocol' : 'http', 'LoadBalancerPort' : 80, 'InstanceProtocol' : 'http', 'InstancePort' : 80},], Subnets=[subnet_public.id, subnet_public2.id], SecurityGroups=[sec_group_lb.id] )
describe_lb = client.describe_load_balancers()
print(describe_lb['LoadBalancerDescriptions'][0]['LoadBalancerName'])
# register instance to load balancer
register_lb = client.register_instances_with_load_balancer(LoadBalancerName=describe_lb['LoadBalancerDescriptions'][0]['LoadBalancerName'], Instances=[{'InstanceId': instances[0].id }] )




