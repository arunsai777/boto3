# boto3
Create AWS Infrastructure using boto3

Creates a VPC with public and private subnets

Creates a role and grants access to perform operations on a EC2 instance.

Launches an ec2 instance with the role created, inside the private subnet of VPC, and installs apache through bootstrapping.

Creates a load balancer in public subnet.

Adds the ec2 instance, under the load balancer
