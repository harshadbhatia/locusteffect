"""
The scripts implements functionality fo AWS usage for locust
:TODO: Security group authorize checks
:ssh-add for windows machines
:When creating new slaves the range should begin from last of existing slaves
"""
import subprocess
import time
import itertools

import boto.ec2

AWS_ACCESS_KEY_ID = ''
AWS_SECRET_ACCESS_KEY = ''

AWS_REGION = 'ap-southeast-2'

SLAVE_INSTANCES = {}
KEY_SAVE_DIRECTORY = ''  # '/Users/blahblah/.ssh/'
AMI_INSTANCE_ID = 'ami-1711732d'

MASTER_NAME = 'locust_master'
SLAVE_NAME_PREFIX = 'locust_slave'

KEY_NAME = 'locust'
SG_NAME = 'locust'

NO_OF_SLAVES = 2
A_RULES = [['tcp', 22, 22, '0.0.0.0/0'],
           ['tcp', 5557, 5558, '0.0.0.0/0'],
           ['tcp', 8089, 8089, '0.0.0.0/0']]


def get_or_create_key_pair(aws_region=AWS_REGION, key_name=KEY_NAME, key_save_directory=KEY_SAVE_DIRECTORY):
    """
    The method gets or create a new key pair for ssh connections
    :param aws_region:
    :return: key_pair:
    """
    conn = create_connection(aws_region)
    # Get any existing key pair with same name
    key_pair = conn.get_key_pair(key_name)

    if not key_pair:
        key_pair = conn.create_key_pair(key_name)
        key_pair.save(key_save_directory)

    subprocess.call(['ssh-add', '{0}{1}.pem'.format(key_save_directory, key_pair.name)])

    return key_pair


def get_or_create_security_group(aws_region=AWS_REGION, sg_name=SG_NAME):
    """
    The method deletes and then recreates the group as required saves lot of time checking every single rule
    :param aws_region:
    :return: group: security group with name defined above
    :TODO: Authorize checks - Currently assumes if group present has appropriate authorization rules
    """
    conn = create_connection(aws_region)
    group = [g for g in conn.get_all_security_groups() if g.name == sg_name]
    if not group:
        group = conn.create_security_group(SG_NAME, 'Group for Locust')
        for a_rule in A_RULES:
            group.authorize(a_rule[0], a_rule[1], a_rule[2], a_rule[3])
    else:
        group = group[0]

    return group


def create_connection(aws_region=AWS_REGION, aws_access_key_id=AWS_ACCESS_KEY_ID,
                      aws_secret_access_key=AWS_SECRET_ACCESS_KEY):
    """
    The method creates an EC2 instance
    :param aws_region:
    :param aws_access_key_id:
    :param aws_secret_access_key:
    :return: conn: boto EC2 connection instance
    """
    conn = boto.ec2.connect_to_region(aws_region, aws_access_key_id=aws_access_key_id,
                                      aws_secret_access_key=aws_secret_access_key)
    return conn


def get_master_dns_ip(aws_region=AWS_REGION, master_name=MASTER_NAME):
    """
    The method returns master server values
    :param aws_region:
    :return: master_dns:
    :return: master_ip:
    """

    master_ip = ''
    master_dns = ''
    conn = create_connection(aws_region)
    reservation = conn.get_all_instances()
    # Yeah I don't know why they have these stupid reservation objects either...

    for res in reservation:
        for instance in res.instances:
            status = instance.update()
            if status == 'running' and master_name in instance.tags.itervalues():
                master_ip = instance.private_ip_address
                master_dns = instance.public_dns_name

    return master_dns, master_ip


def get_slave_dns_list(aws_region=AWS_REGION, slave_name_prefix=SLAVE_NAME_PREFIX):
    """
    The method returns slave DNS list from AWS
    :param aws_region:
    :return: A list of AWS instances DNS
    """
    slave_list = []
    conn = create_connection(aws_region)
    reservation = conn.get_all_instances()
    # Yeah I don't know why they have these stupid reservation objects either...

    for res in reservation:
        for instance in res.instances:
            status = instance.update()

            if status == 'running':
                slave_list.append(
                    [instance.public_dns_name for val in instance.tags.values() if slave_name_prefix in val])

    return list(itertools.chain.from_iterable(slave_list))


def create_instance(conn, ami, tag, key_name=KEY_NAME, sg=SG_NAME):
    """
    The method creates an instance based on AMI_ID and tag provided
    :param conn:
    :param ami:
    :param tag:
    :return: ec2_instance:
    """
    reservation = conn.run_instances(ami, key_name=key_name, instance_type='t2.micro',
                                     security_groups=[sg])
    ec2_instance = reservation.instances[0]

    status = ec2_instance.update()
    while status == 'pending':
        time.sleep(10)
        status = ec2_instance.update()

    if status == 'running':
        conn.create_tags([ec2_instance.id], {'Name': tag})

    time.sleep(20)

    return ec2_instance


def create_master(aws_region=AWS_REGION, ami_instance_id=AMI_INSTANCE_ID, master_name=MASTER_NAME):
    """
    The method create a master instance for running our locust in distributed mode and returns the value
    :param aws_region:
    :return: instance: EC2 Instance
    """
    conn = create_connection(aws_region)
    instance = create_instance(conn, ami_instance_id, master_name)

    return instance


def create_slaves(no_of_slaves=NO_OF_SLAVES, aws_region=AWS_REGION, ami_instance_id=AMI_INSTANCE_ID,
                  slave_name_prefix=SLAVE_NAME_PREFIX):
    """
    The method creates slaves based on defaults provided
    :param no_of_slaves:
    :param aws_region:
    :return:
    """
    conn = create_connection(aws_region)

    # Launch slave instances
    for slave_no in range(0, no_of_slaves):
        slave_instance = create_instance(conn, ami_instance_id, '{0}_{1}'.format(slave_name_prefix, slave_no))
        SLAVE_INSTANCES[slave_no] = slave_instance
