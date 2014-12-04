#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Longgeek <longgeek@gmail.com>

from time import strftime
from time import localtime

from bat.lib.sing_leton import DockerSingLeton


class Container_Manager(object):
    """ Docker 管理类"""

    def __init__(self):
        self.connection = DockerSingLeton()

    def _containers(self, cid=None):
        """获取所有 Container 的信息
        # docker ps -a
        # docker ps -a | grep $cid

        """
        try:
            all_containers = self.connection.containers(
                all=True, size=True)
            if cid:
                for c in xrange(len(all_containers)):
                    if all_containers[c]['Id'] == cid:
                        return (0, '', all_containers[c])
            else:
                return (0, '', all_containers)

        except Exception, e:
            return (1, e, '')

    def _inspect_container(self, cid):
        """获取一个 Container 的信息
        # docker inspect $cid

        """

        try:
            container = self.connection.inspect_container(cid)
            return (0, '', container)
        except Exception, e:
            return (1, e, '')

    def create_container(self, msg):
        """创建 Container"""

        try:
            c_id = self.connection.create_container(
                name=msg['name'],
                image=msg['image_name'],
                ports=msg['ports'],
                command=msg['command'],
                tty=True,
                detach=True,
                stdin_open=True,
            )['Id']

            # 启动 Container
            start_c = self.start_container(msg=msg, c_id=c_id)

            if start_c[0] == 0:
                msg['cid'] = c_id

                # 调用 _containers, 拿到 size status command created
                containers = self._containers(c_id)
                if containers[0] == 0:
                    msg['size'] = containers[2]['SizeRootFs']
                    msg['status'] = containers[2]['Status']
                    msg['command'] = containers[2]['Command']
                    msg['created'] = strftime(
                        '%Y-%m-%d %X', localtime(containers[2]['Created']))
                else:
                    return containers

                # 调用 _inspect_c, 拿到 name hostname
                inspect_c = self._inspect_container(c_id)
                if inspect_c[0] == 0:
                    msg['name'] = inspect_c[2]['Name'][1:]
                    msg['hostname'] = inspect_c[2]['Config']['Hostname']
                else:
                    return inspect_c

                return (0, '', msg)
            else:
                return start_c

        except Exception, e:
            return (1, e, '')

    def start_container(self, msg, c_id=None):
        """启动 Container"""

        if not msg['cid']:
            container_id = c_id
        if not c_id:
            container_id = msg['cid']

        try:
            self.connection.start(container=container_id)
            return (0, '', msg)

        except Exception, e:
            return (1, e, '')

    def stop_container(self, msg):
        """停止 Container"""
        pass

    def restart_container(self, msg):
        """重启 Container"""
        pass

    def delete_container(self, msg):
        """删除 Container"""
        try:
            self.connection.remove_container(container=msg['cid'],
                                             force=True)
            return (0, '', msg)
        except Exception, e:
            return (1, e, '')

    def exec_container(self, msg):
        """增加进程 Container"""
        pass


def main(msg):
    """Containers 程序入口,
    用来传递 message 类型

    """
    msg_type = msg['message_type']
    tt = Container_Manager()
    return getattr(tt, msg_type)(msg)
