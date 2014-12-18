#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Longgeek <longgeek@gmail.com>

import re
import os
import simplejson

from bat.lib.sing_leton import DockerSingLeton


class Container_Manager(object):
    """ Docker 管理类"""

    def __init__(self):
        self.connection = DockerSingLeton()
        self.range_ports = xrange(4301, 4319)
        self.container_path = '/var/lib/docker/aufs/diff'

    def _containers(self, db_id, cid=None):
        """获取所有 Container 的信息, 或一个容器
        # docker ps -a
        # docker ps -a | grep $cid

        """
        try:
            # 获取一个容器的信息
            if cid:
                container = self.connection.containers(all=True,
                                                       size=True,
                                                       filters={'id': cid})
                if len(container) == 1:
                    container = container[0]
                return (0, '', container)
            # 获取所有容器的信息
            else:
                all_containers = self.connection.containers(all=True,
                                                            size=True)
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
            command = msg['command']
            if not command:
                command = '/bin/bash'
            c_id = self.connection.create_container(
                name=msg['name'],
                image=msg['image_name'],
                ports=msg['ports'],
                command=command,
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
                                                          msg['username'],
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

    def _get_console_port(self, db_id, c_id, host, username, processes):
        """获取所有 console 的端口和映射端口"""

        # 定义 return 数据
        result = {'id': db_id,
                  'cid': c_id,
                  'host': host,
                  'console': {},
                  'use_ports': [],
                  'free_ports': [],
                  'username': username,
                  'message_type': 'console_container'}

        if not processes:
            result['free_ports'] = self.range_ports
            return (0, '', result)

        # 过滤进程中指定的端口号，保存到 use_ports 列表中
        use_ports = []
        for process in processes:
            port_group = re.search(r'--port=(\d+) --login', process)
            if port_group:
                port = int(port_group.group(1))
                use_ports.append(port)

            # 获取具体的命令, e.g. 'vim /opt/scripts.py'
            command = process.split('--login=False --cmd=')[-1]

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
            base_command = "butterfly.server.py --unsecure \
--host=0.0.0.0 --port=%s --login=False --cmd='%s'"

            # 调用 _get_console_process 获取容器所有的 console 进程
            status, message, result = self._get_console_process(msg)
            if status == 0:
                # 调用 _get_console_port 获取容器所有的 console 端口
                s, m, r = self._get_console_port(db_id,
                                                 c_id,
                                                 msg['host'],
                                                 msg['username'],
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

    def files_write_container(self, msg):
        """为容器中的文件写入数据"""

        try:
            c_id = msg['cid']
            files = msg['files']

            # Docker 容器在 Host 上的路径
            host_dir_path = os.path.join(self.container_path, c_id)

            # 遍历所有的文件
            for file in files:
                # 容器中的文件路径
                container_file_path = os.path.dirname(file)
                # 容器中的文件名字
                container_file_name = os.path.basename(file)
                # 文件所在 Host 上目录的完全路径
                full_path = host_dir_path + container_file_path
                # 文件所在 Host 上的完全路径
                full_file_path = os.path.join(full_path, container_file_name)

                # 如果 full_path 不存在, 就创建
                if not os.path.exists(full_path):
                    os.makedirs(full_path)

                # 写入数据到文件中
                fo = open(full_file_path, 'w')
                fo.writelines(files[file].encode('utf-8'))
                fo.close()
            return (0, '', msg)
        except Exception, e:
            return (1, {'error': str(e), 'id': msg['id']}, '')

    def files_read_container(self, msg):
        """读取容器中文件的内容"""

        try:
            c_id = msg['cid']
            files = msg['files']

            # Docker 容器在 Host 上的路径
            host_dir_path = os.path.join(self.container_path, c_id)

            files_content = {}
            # 遍历所有的文件
            for file in files:
                # 容器中的文件路径
                container_file_path = os.path.dirname(file)
                # 容器中的文件名字
                container_file_name = os.path.basename(file)
                # 文件所在 Host 上目录的完全路径
                full_path = host_dir_path + container_file_path
                # 文件所在 Host 上的完全路径
                full_file_path = os.path.join(full_path, container_file_name)

                # 如果 full_path 不存在, 就创建
                if not os.path.exists(full_path):
                    os.makedirs(full_path)
                # 如果文件不存在, 创建一个空文件
                if not os.path.exists(full_file_path):
                    os.mknod(full_file_path, 0644)

                s, m, r = self._exec_file_content(msg['id'], c_id, file)
                files_content[file] = r
            msg['files'] = files_content
            return (0, '', msg)

        except Exception, e:
            return (1, {'error': str(e), 'id': msg['id']}, '')

    def _exec_file_content(self, db_id, c_id, filename):
        """通过 Docker execute api 获取容器中文件内容"""

        try:
            content = self.connection.execute(c_id, 'cat %s' % filename)
            return (0, '', content)
        except Exception, e:
            return (1, {'error': str(e), 'id': id}, '')


def main(msg):
    """Containers 程序入口,
    用来传递 message 类型

    """
    msg_type = msg['message_type']
    exec_action = Container_Manager()
    return getattr(exec_action, msg_type)(msg)
