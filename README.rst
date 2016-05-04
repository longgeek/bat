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
* https://github.com/thstack/groceries
* git@git.pyindex.com:reviewdev/looker.git (online)
* git@git.pyindex.com:reviewdev/boss.git (online manager)
* git@git.pyindex.com:reviewdev/telegraph_pole (restful api)
* git@git.pyindex.com:reviewdev/mountain_tai.git (scheduler)
* https://github.com/thstack/butterfly/tree/thstack/develop (console)
How to use (For Ubuntu-14.04.1 Server)
--------------------------------------
Add Docker apt source:
    curl -s https://get.docker.io/ubuntu/ | sudo sh

If necessary, please update the system as well as the kernel:
    apt-get upgrade
    apt-get dist-upgrade

Install the docker and other dependent software package:
    apt-get install lxc-docker-1.6.2 python-pip git
    apt-get install python-dev libffi-dev libssl-dev libxml2-dev libxslt1-dev

Dependent on the installation of the groceries:
    mkdir /opt/git && cd /opt/git
    git clone https://github.com/thstack/groceries

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

Sure Docker Host the "/storage/.system/.console/" exist.
Use virtualenv build butterfly in the /storage/.system/.console/local/butterfly:

    mkdir -p /storage/.system
    pip install virtualenv
    virtualenv /storage/.system/.console
    source /storage/.system/.console/bin/activate
    cd /storage/.system/.console/local/
    git clone git@github.com:thstack/butterfly.git
    cd butterfly
    pip install -r requirements.txt
    python setup.py develop
    deactivate

Sure Docker Host the "/storage/.virtualenv/" exist.
The Django Practice topic is heavily dependent on it:

    # django-1.8.2
    mkdir -p /storage/.system/.virtualenv/django
    virtualenv /storage/.system/.virtualenv/django/django-1.8.2
    source /storage/.system/.virtualenv/django/django-1.8.2/bin/activate
    pip install "django==1.8.2"
    pip install ipdb
    deactivate
    sed -i "s/'django.middleware.clickjacking.XFrameOptionsMiddleware'/# 'django.middleware.clickjacking.XFrameOptionsMiddleware'/g" /storage/.system/.virtualenv/django/django-1.8.2/lib/python2.7/site-packages/django/conf/project_template/project_name/settings.py

    # django-1.8.4
    virtualenv /storage/.system/.virtualenv/django/django-1.8.4
    source /storage/.system/.virtualenv/django/django-1.8.4/bin/activate
    pip install "django==1.8.4"
    pip install ipdb
    deactivate
    sed -i "s/'django.middleware.clickjacking.XFrameOptionsMiddleware'/# 'django.middleware.clickjacking.XFrameOptionsMiddleware'/g" /storage/.system/.virtualenv/django/django-1.8.4/lib/python2.7/site-packages/django/conf/project_template/project_name/settings.py

Sure tree command the >= 1.7.0.
Install:

    wget https://launchpadlibrarian.net/173977087/tree_1.7.0.orig.tar.gz
    tar zxvf tree_1.7.0.orig.tar.gz
    cd tree-1.7.0
    make
    make install
Log:
    tail -f /var/log/bat/bat.log
