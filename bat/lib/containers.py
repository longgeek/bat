#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Longgeek <longgeek@gmail.com>

import simplejson

from bat.lib.sing_leton import DockerSingLeton


class Container_Manager(object):
    """ Docker 管理类"""

    def __init__(self):
        self.connection = DockerSingLeton()

    def _containers(self, db_id, cid=None):
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
            return (1, {'error': str(e), 'id': db_id}, '')

    def _inspect_container(self, db_id, cid):
        """获取一个 Container 的信息
        # docker inspect $cid

        """

        try:
            container = self.connection.inspect_container(cid)
            return (0, '', container)
        except Exception, e:
            return (1, {'error': str(e), 'id': db_id}, '')

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
                containers = self._containers(msg['id'], c_id)
                if containers[0] == 0:
                    msg['size'] = containers[2]['SizeRootFs']
                    msg['command'] = containers[2]['Command']
                    msg['created'] = containers[2]['Created']
                else:
                    return containers

                # 调用 _inspect_c, 拿到 name hostname
                inspect_c = self._inspect_container(msg['id'], c_id)
                if inspect_c[0] == 0:
                    msg['name'] = inspect_c[2]['Name']
                    msg['hostname'] = inspect_c[2]['Config']['Hostname']
                else:
                    return inspect_c

                return (0, '', msg)
            else:
                return start_c

        except Exception, e:
            return (1, {'error': str(e), 'id': msg['id'],
                        'message_type': 'create_container'}, '')

    def start_container(self, msg, c_id=None, publish_all_ports=True):
        """启动 Container"""

        if not msg['cid']:
            container_id = c_id
        if not c_id:
            container_id = msg['cid']

        try:
            self.connection.start(container=container_id,
                                  publish_all_ports=True)
            containers = self._containers(msg['id'], container_id)
            if containers[0] == 0:
                msg['status'] = containers[2]['Status']
            else:
                return containers
            return (0, '', msg)

        except Exception, e:
            return (1, {'error': str(e), 'id': msg['id']}, '')

    def stop_container(self, msg, timeout=5):
        """停止 Container"""
        try:
            c_id = msg['cid']
            self.connection.stop(c_id, timeout)

            # 调用 _containers, 拿到 status
            containers = self._containers(msg['id'], c_id)
            if containers[0] == 0:
                msg['status'] = containers[2]['Status']
            return (0, '', msg)

        except Exception, e:
            return (1, {'error': str(e), 'id': msg['id']}, '')

    def restart_container(self, msg, timeout=5):
        """重启 Container"""
        try:
            c_id = msg['cid']
            self.connection.restart(c_id, timeout)

            # 调用 _containers, 拿到 status
            containers = self._containers(msg['id'], c_id)
            if containers[0] == 0:
                msg['status'] = containers[2]['Status']
            return (0, '', msg)

        except Exception, e:
            return (1, {'error': str(e), 'id': msg['id']}, '')

    def delete_container(self, msg):
        """删除 Container"""
        try:
            # 调用 _inspect_c, 判断容器是否暂停
            inspect_c = self._inspect_container(msg['id'], msg['cid'])
            if inspect_c[0] == 0:
                if inspect_c[2]['State']['Paused']:
                    unpause_result = self.unpause_container(msg)
                    if unpause_result[0] != 0:
                        return unpause_result
                self.connection.remove_container(container=msg['cid'],
                                                 force=True)
            else:
                return inspect_c
            return (0, '', msg)
        except Exception, e:
            return (1, {'error': str(e), 'id': msg['id']}, '')

    def exec_container(self, msg):
        """增加进程 Container"""
        try:
            c_id = msg['cid']
            c_list = simplejson.loads(msg['command'])
            for c in c_list:
                self.connection.execute(container=c_id, cmd=c,
                                        detach=True, tty=True,
                                        stderr=False, stdout=False)
            return (0, '', msg)
        except Exception, e:
            return (1, {'error': str(e), 'id': msg['id']}, '')

    def pause_container(self, msg):
        """暂停容器"""
        try:
            c_id = msg['cid']
            self.connection.pause(c_id)

            # 调用 _containers, 拿到 status
            containers = self._containers(msg['id'], c_id)
            if containers[0] == 0:
                msg['status'] = containers[2]['Status']
            return (0, '', msg)

        except Exception, e:
            return (1, {'error': str(e), 'id': msg['id']}, '')

    def unpause_container(self, msg):
        """恢复暂停的容器"""
        try:
            c_id = msg['cid']
            self.connection.unpause(c_id)

            # 调用 _containers, 拿到 status
            containers = self._containers(msg['id'], c_id)
            if containers[0] == 0:
                msg['status'] = containers[2]['Status']
            return (0, '', msg)

        except Exception, e:
            return (1, {'error': str(e), 'id': msg['id']}, '')


def main(msg):
    """Containers 程序入口,
    用来传递 message 类型

    """
    msg_type = msg['message_type']
    exec_action = Container_Manager()
    return getattr(exec_action, msg_type)(msg)
