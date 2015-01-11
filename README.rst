====
BAT
====

Bat != Baidu Ali Tencent

Why bat? It is like a batman, absorb the server resources.

Getting Started
---------------

If you'd like to run from the master branch, you can clone the git repo:

    git clone git@git.pyindex.com:reviewdev/bat.git


* Wiki: http://wiki.pyindex.com


AMQP Client - Python Pika
-------------
https://github.com/pika/pika

References
----------
* http://wiki.pyindex.com

We have integration with
------------------------
* git@git.pyindex.com:reviewdev/looker.git (online)
* git@git.pyindex.com:reviewdev/boss.git (online manager)
* git@git.pyindex.com:reviewdev/telegraph_pole (restful api)
* git@git.pyindex.com:reviewdev/mountain_tai.git (scheduler)

How to use (For Ubuntu-14.04.1 Server)
--------------------------------------
Add Docker apt source:
    curl -s https://get.docker.io/ubuntu/ | sudo sh

If necessary, please update the system as well as the kernel:
    apt-get upgrade
    apt-get dist-upgrade

Install the docker and other dependent software package:
    apt-get install lxc-docker-1.4.0 python-pip git

Dependent on the installation of the bat:
    git clone git@git.pyindex.com:reviewdev/bat.git
    cd bat/
    python setup.py egg_info
    pip install -r bat.egg-info/requires.txt
    python setup.py install (Develop mode: python setup.py develop)

The configuration file:
    mkdir /etc/bat
    cp etc/bat/bat.conf.sample /etc/bat/bat.conf
    cp etc/init/bat-worker.conf /etc/init/
    cp etc/logrotate.d/bat-worker /etc/logrotate.d/
    cp sbin/bat-worker /usr/sbin/
    mkdir /var/log/bat
    chown :adm /var/log/bat
    touch /var/log/bat/bat-worker.log
    logrotate -f /etc/logrotate.d/bat-worker
    service rsyslog restart

Modify the configuration file:
    vim /etc/bat/bat.conf
    e.g.:
    amqp_interface = your_network_card_name
    rabbit_host = your_rabbitmq_server
    ....

Run it:
    service bat-worker restart

Log:
    tail -f /var/log/bat/bat.log
