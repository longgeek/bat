#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Longgeek <longgeek@gmail.com>

import os
import fcntl
import socket
import struct
import ConfigParser


class BatConfig(object):
    """专门处理 bat.conf 的类"""

    def __init__(self):
        """初始化读取配置文件"""

        self.status, self.msgs, self.results = self._get_file()
        if self.status == 0:
            self.cf = ConfigParser.ConfigParser()
            self.cf.read(self.results)

    def _get_file(self):
        """判断文件是否存在"""

        bat_conf = '/etc/bat/bat.conf'
        if os.path.exists(bat_conf):
            return (0, '', bat_conf)
        else:
            return (-1, "/etc/bat/bat.conf: No such file or directory", '')

    def get_rabbit_url(self, url=True):
        """返回 rabbitmq 地址"""

        if self.status != 0:
            return (self.status, self.msgs, self.results)
        try:
            rabbit_host = self.cf.get('rabbitmq', 'rabbit_host')
            rabbit_port = self.cf.get('rabbitmq', 'rabbit_port')
            rabbit_user = self.cf.get('rabbitmq', 'rabbit_userid')
            rabbit_pass = self.cf.get('rabbitmq', 'rabbit_password')

            # 判断是否要返回完整路径
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
        except Exception, e:
            return (1, str(e), '')

    def get_ip(self):
        """获取当前主机 IP 地址"""

        if self.status != 0:
            return (self.status, self.msgs, self.results)

        try:
            interface = self.cf.get('DEFAULT', 'amqp_interface')
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            ip = socket.inet_ntoa(fcntl.ioctl(s.fileno(),
                                              0x8915,
                                              struct.pack('256s',
                                                          interface[:15])
                                              )[20:24])
            return (0, '', ip)
        except Exception, e:
            return (1, str(e), '')
