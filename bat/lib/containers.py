#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Longgeek <longgeek@gmail.com>

import re
import simplejson

from bat.lib.sing_leton import DockerSingLeton


class Container_Manager(object):
    """ Docker 管理类"""

    def __init__(self):
        self.connection = DockerSingLeton()
        self.range_ports = xrange(4301, 4500)

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

    def exec_container(self, msg, console=False):
        """增加进程 Container"""
        try:
            c_id = msg['cid']
            if not console:
                c_list = simplejson.loads(msg['command'])
            else:
                c_list = msg['console_command']

            if c_list:
                for c in c_list:
                    self.connection.execute(container=c_id, cmd=c,
                                            detach=True, tty=True,
                                            stderr=False, stdout=False)
            # 检查进程是否成功启动
            if console:
                # 调用 _get_console_process 获取容器所有的 console 进程
                s, m, r = self._get_console_process(msg)
                if s == 0:
                    # 调用 _get_console_port 获取容器所有的 console 端口
                    process_info = self._get_console_port(msg['id'],
                                                          c_id,
                                                          msg['host'],
                                                          r)
                    if process_info[0] == 0:
                        process_info[2].pop('use_ports')
                        process_info[2].pop('free_ports')
                    return (0, '', process_info[2])

                else:
                    return(s, m, r)
            else:
                return (0, '', msg)

        except Exception, e:
            return (1, {'error': str(e), 'id': msg['id']}, '')

    def top_container(self, msg):
        """列出容器中的进程"""
        try:
            c_id = msg['cid']
            top_result = self.connection.top(c_id)
            msg['titles'] = top_result['Titles']
            msg['processes'] = top_result['Processes']
            return (0, '', msg)

        except Exception, e:
            return (1, {'error': str(e), 'id': msg['id']}, '')

    def _get_console_process(self, msg):
        """获取所有 console 进程"""

        try:
            # 拿出容器所有的进程
            s, m, r = self.top_container(msg)
            if s == 0:
                processes = r['processes']
                processes_list = []
                # 从所有进程中过滤出包含 'nsenter-exec' 关键字的进程
                # 保存结果到 processes_list 中
                for p in xrange(len(processes)):
                    process = processes[p][-1]
                    if 'nsenter-exec' in process:
                        process = process.split(' -- ', 1)[1]
                        processes_list.append(process)
                # 返回过滤的进程
                return (0, '', processes_list)
            else:
                return (s, m, r)

        except Exception, e:
            return (1, {'error': str(e), 'id': msg['id']}, '')

    def _get_port(self, db_id, c_id, private_port):
        """获取容器端口所映射的端口 """
        try:
            r = self.connection.port(c_id, private_port)
            return (0, '', r[0]['HostPort'])
        except Exception, e:
            return (1, {'error': str(e), 'id': db_id}, '')

    def _get_console_port(self, db_id, c_id, host, processes):
        """获取所有 console 的端口和映射端口"""

        # 定义 return 数据
        result = {'id': db_id,
                  'cid': c_id,
                  'host': host,
                  'console': {},
                  'use_ports': [],
                  'free_ports': []}

        if not processes:
            result['free_ports'] = self.range_ports
            return (0, '', result)

        # 过滤进程中指定的端口号，保存到 use_ports 列表中
        use_ports = []
        for process in processes:
            port_group = re.search(r'-p (\d+) -t', process)
            if port_group:
                port = int(port_group.group(1))
                use_ports.append(port)

            # 获取具体的命令, e.g. 'vim /opt/scripts.py'
            command = process.split('/:root:root:/root:')[-1]

            # 获取映射端口
            s, m, r = self._get_port(db_id, c_id, port)
            if s == 0:
                result['console'][command] = {'public_port': int(r),
                                              'private_port': port}
            else:
                return (s, m, r)

        # 算出空闲的端口, 保存, return 数据
        free_ports = set(self.range_ports) - set(sorted(use_ports))
        free_ports = list(free_ports)
        result['use_ports'] = use_ports
        result['free_ports'] = free_ports
        return (0, '', result)

    def console_container(self, msg):
        """为容器添加相应 Console"""
        try:
            db_id = msg['id']
            c_id = msg['cid']
            base_command = "shellinaboxd -v -p %d -t -s '/:root:root:/root:%s'"

            # 调用 _get_console_process 获取容器所有的 console 进程
            status, message, result = self._get_console_process(msg)
            if status == 0:
                # 调用 _get_console_port 获取容器所有的 console 端口
                s, m, r = self._get_console_port(db_id,
                                                 c_id,
                                                 msg['host'],
                                                 result)
                if s == 0:
                    exist_command = r['console'].keys()
                    exec_command = simplejson.loads(msg['command'])
                    free_ports = r['free_ports']
                    will_command = []
                    for i in xrange(len(exec_command)):
                        if exec_command[i] not in exist_command:
                            command = base_command % (free_ports[i],
                                                      exec_command[i])
                            will_command.append(command)

                    msg['console_command'] = will_command
                    exec_result = self.exec_container(msg, console=True)
                    return exec_result
                else:
                    return (s, m, r)
            else:
                return (status, message, result)
        except Exception, e:
            return (1, {'error': str(e), 'id': msg['id']}, '')


def main(msg):
    """Containers 程序入口,
    用来传递 message 类型

    """
    msg_type = msg['message_type']
    exec_action = Container_Manager()
    return getattr(exec_action, msg_type)(msg)
