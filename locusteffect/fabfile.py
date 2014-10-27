"""
Fabric file which runs all tasks
Modify values as required in aws.py or fabfile.py

usage: fab setup deloy_master deploy_slaves launch

Add more slaves in existing test
usage: fab add_slaves:no_of_slaves=1 launch
"""

import webbrowser

from fabric.api import *

from aws import *


env.user = 'ubuntu'
env.timeout = 60
env.connection_attempts = 10


def run_master_tasks():
    """
    The method installs all the necessary updates/libs and finally start a screen session for locust as master
    """
    setup_image()
    run('screen -S loc_session -d -m locust -f /home/ubuntu/locusteffect/locustfile.py --master; sleep 1')


def run_slave_tasks():
    """
    The method installs all the necessary updates/libs and finally start a screen session for locust as slave
    """
    _, master_ip = get_master_dns_ip()
    if master_ip:
        setup_image()
        run('screen -S loc_session -d -m locust -f /home/ubuntu/locusteffect/locustfile.py --slave --master-host={0} ; '
            'sleep 1'.format(
            master_ip))
    else:
        print 'Well setup a Master first'


def setup_image():
    """
    The method installs all the required libraries and tries to kill any existing screen session,
    incase command is run twice
    """

    sudo('apt-get update')
    sudo('apt-get upgrade -y')
    sudo('apt-get install -y gcc python2.7-dev python-setuptools build-essential')

    sudo('easy_install pip')
    sudo('Y | pip install pyzmq --install-option="--zmq=bundled"')
    put('../requirements.txt', '')
    sudo('Y | pip install -r requirements.txt')

    try:
        # Kill all
        run("screen -ls | grep '[0-9]*\.loc_session' | cut -d. -f1 | awk '{print $1}' | xargs kill; sleep 1")
    # .TODO: proper exception
    except:
        pass

    put('../locusteffect', '')


@task
def setup():
    """
    This method does the initial setup for AWS instances
    """
    KEY_NAME = get_or_create_key_pair().name
    SG_NAME = get_or_create_security_group().name


@task
def deploy_master():
    """
    The method creates master instance if not found based on tag defined in aws_functions file
    """
    master_dns, master_ip = get_master_dns_ip()
    if not master_ip:
        master_instance = create_master()
        host_list = [master_instance.public_dns_name]
        execute(run_master_tasks, hosts=host_list)
    else:
        print 'Found existing running master, Running Tasks as usual'
        execute(run_master_tasks, hosts=[master_dns])


@task
def deploy_slaves():
    """
    The method deploys slaves if not found or already created
    """
    # Time for our slaves
    _, master_ip = get_master_dns_ip()
    if master_ip:
        # Test and see if we can find existing slaves
        slave_list = get_slave_dns_list()
        if NO_OF_SLAVES - len(slave_list) > 0:
            print 'Found {0} existing slaves creating {1} new slaves'.format(len(slave_list),
                                                                            NO_OF_SLAVES - len(slave_list))
            create_slaves(NO_OF_SLAVES - len(slave_list))
            host_list = [slave.public_dns_name for slave in SLAVE_INSTANCES.itervalues()] + slave_list
        else:
            print 'No more slaves needed'
            host_list = slave_list

        execute(run_slave_tasks, hosts=host_list)
    else:
        print 'Setup a Master first'


@task
def add_slaves(no_of_slaves=''):
    """
    Creates any additional slaves, used when tests are running and more slaves are required to run requests
    :param no_of_slaves:
    """
    _, master_ip = get_master_dns_ip()
    if master_ip and no_of_slaves:
        # Test and see if we can find existing slaves
        create_slaves(int(no_of_slaves))
        host_list = [slave.public_dns_name for slave in SLAVE_INSTANCES.itervalues()]
        execute(run_slave_tasks, hosts=host_list)
    else:
        print 'Setup a Master first'


@task
def launch():
    """
    The method just opens up the browser once all tasks are finished
    """

    public_dns, _ = get_master_dns_ip()
    url = 'http://{0}:8089'.format(public_dns)

    webbrowser.open_new(url)