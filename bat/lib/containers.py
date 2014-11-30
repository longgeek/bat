#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Longgeek <longgeek@gmail.com>

from bat.lib.sing_leton import DockerSingLeton


class Container_Manager(object):
    """ Docker 管理类"""

    def __init__(self):
        self.connection = DockerSingLeton()

    def create_container(self, msg):
        # 创建一个 Container
        try:
            c_id = self.connection.create_container(
                name=msg['name'],
                image=msg['image_name'],
                ports=msg['ports'],
                command=msg['command'],
                tty=True,
                detach=True,
                stdin_open=True,
            )
        except Exception, msgs:
            return (1, msgs, '')

        # 启动 Container
        try:
            self.connection.start(container=c_id)
            msg['cid'] = c_id['Id']
            return (0, '', msg)

        except Exception, msgs:
            return (1, msgs, '')


def main(msg):
    msg_type = msg['message_type']
    tt = Container_Manager()
    return getattr(tt, msg_type)(msg)
