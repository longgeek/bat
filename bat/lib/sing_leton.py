#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Longgeek <longgeek@gmail.com>

import pika

from bat import cfg
from docker import Client

bat_conf = cfg.BatConfig()
get_url = bat_conf.get_rabbit_url(url=False)
if get_url[0] == 0:
    RABBITMQ_URLS = get_url[2]


class DockerSingLeton(object):
    """ 单例类, 只初始化一次

    获取 Docker Host 连接对象
    """

    _instance = None
    conn = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(DockerSingLeton, cls).__new__(
                cls, *args, **kwargs)

            # Initialize Docker Host connection
            cls.conn = Client(base_url='unix:///var/run/docker.sock')
        return cls.conn


class RabbitSingLeton(object):
    """ 单例类，只初始化一次

    获取 RabbitMQ 连接对象.
    """

    _instance = None
    conn = None
    channel = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(RabbitSingLeton, cls).__new__(
                cls, *args, **kwargs)

            # Initialize RabbitMQ connection
            credentials = pika.PlainCredentials(RABBITMQ_URLS['user'],
                                                RABBITMQ_URLS['pass'])
            cls.conn = pika.BlockingConnection(pika.ConnectionParameters(
                host=RABBITMQ_URLS['host'],
                port=int(RABBITMQ_URLS['port']),
                credentials=credentials))

            cls.channel = cls.conn.channel()

        return (cls.channel, cls.conn)
