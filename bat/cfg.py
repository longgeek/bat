#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Longgeek <longgeek@gmail.com>

import os
import ConfigParser


def get_file():
    bat_conf = '/etc/bat/bat.conf'
    if os.path.exists(bat_conf):
        return (0, '', bat_conf)
    else:
        return (-1, "The '/etc/bat/bat.conf' configuration file not found", '')


def get_rabbit_url(url=True):
    bat_conf = get_file()
    if bat_conf[0] == 0:
        cf = ConfigParser.ConfigParser()
        cf.read(bat_conf[2])
        rabbit_host = cf.get('rabbitmq', 'rabbit_host')
        rabbit_port = cf.get('rabbitmq', 'rabbit_port')
        rabbit_user = cf.get('rabbitmq', 'rabbit_userid')
        rabbit_pass = cf.get('rabbitmq', 'rabbit_password')
        if url:

            rabbit_kombu_url = "amqp://%s:%s@%s:%s" % (rabbit_user,
                                                       rabbit_pass,
                                                       rabbit_host,
                                                       rabbit_port)
            return (0, '', rabbit_kombu_url)
        else:
            return (0, '', {'host': rabbit_host,
                            'port': rabbit_port,
                            'user': rabbit_user,
                            'pass': rabbit_pass})

    else:
        return (-1, bat_conf[1], '')
