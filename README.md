locusteffect
============

Creates AWS EC2 Instances and start locust.io in a distributed setting for Load testing
** It may cost money on AWS

Usage
-----

First enter the credentials and other values in aws.py. Then,

> fab setup deploy_master deploy_slaves launch
>
> For deploying extra slaves then run
> fab add_slaves:no_of_slaves=1 launch
