#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Longgeek <longgeek@gmail.com>

import re
import os
import time
import random
import signal
import subprocess
import simplejson

from docker.utils import create_host_config
from bat.lib.sing_leton import DockerSingLeton


class Container_Manager(object):
    """ Docker 管理类"""

    def __init__(self):
        self.connection = DockerSingLeton()
        self.range_ports = xrange(4301, 4320)
        self.container_path = '/var/lib/docker/aufs/mnt'
        self.nginx_root = '/usr/share/nginx/html'

    def _containers(self, db_id, cid=None):
        """获取所有 Container 的信息, 或一个容器
        # docker ps -a
        # docker ps -a | grep $cid

        """
        try:
            # 获取一个容器的信息
            if cid:
                container = self.connection.containers(
                    all=True,
                    size=True,
                    filters={'id': cid}
                )
                if len(container) == 1:
                    container = container[0]
                return (0, '', container)
            # 获取所有容器的信息
            else:
                all_containers = self.connection.containers(
                    all=True,
                    size=True
                )
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
                command = 'bash'

            # container_name == 'c-' + db_id + random str
            sample = 'abcdefghijklmnopqrstuvwxyz' + str(int(time.time()))
            random_str = ''.join(random.sample(sample, 11))
            msg['container_name'] = 'c-%s' % str(msg['id']) + random_str
            c_id = self.connection.create_container(
                name=msg['container_name'],
                image=msg['image_name'],
                ports=msg['ports'],
                command=command,
                tty=True,
                detach=True,
                stdin_open=True,
                mem_limit="512m",
                memswap_limit=-1,
                cpuset=0,
                volumes=['/pythonpie/.console', '/pythonpie/.console'],
                host_config=create_host_config(
                    publish_all_ports=True,
                    binds={
                        '/pythonpie/.console': {
                            'bind': '/pythonpie/.console',
                            'ro': True,
                        }
                    }),
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
        """启动 Container
        1. 直接启动容器
        2. 创建一个 web_console 的进程
        3. 获取 80、8000、9000 所对于的外部端口
        """

        if not msg['cid']:
            container_id = c_id
        if not c_id:
            container_id = msg['cid']

        msg['cid'] = container_id
        try:
            self.connection.start(container=container_id)
            s, m, r = self._get_port(msg['id'], msg['cid'], 80)
            if s == 0:
                msg['www_port'] = r
                s, m, r = self.web_console_container(msg)
                if s != 0:
                    return (s, m, r)
                s, m, r = self._get_port(msg['id'], msg['cid'], r)
                if s == 0:
                    msg['ssh_port'] = r
                    s, m, r = self._get_port(msg['id'], msg['cid'], 8000)
                    if s == 0:
                        msg['8000_port'] = r
                        s, m, r = self._get_port(msg['id'], msg['cid'], 9000)
                        if s == 0:
                            msg['9000_port'] = r
                        else:
                            return (s, m, r)
                    else:
                        return (s, m, r)
                else:
                    return (s, m, r)
            else:
                return (s, m, r)
            containers = self._containers(msg['id'], container_id)
            if containers[0] == 0:
                msg['status'] = containers[2]['Status']
            else:
                return containers
            return (0, '', msg)

        except Exception, e:
            return (1,
                    {'error': str(e),
                     'id': msg['id'],
                     'message_type': msg['message_type']},
                    '')

    def web_console_container(self, msg):
        """用来启动用户的 web 登录进程

        1. 检测 下面的 base_command 进程是否存在
        2. 存在，则返回监听的端口
        3. 不存在，创建进程，并返回端口
        """

        base_command = "/pythonpie/.console/bin/butterfly.server.py \
--unsecure --host=0.0.0.0 --port=%s --login=True --cmd='bash'"

        try:
            # 调用 _get_console_process 获取容器的 web_console 进程
            s, m, r = self._get_console_process(msg, web_console=True)
            if s == 0:
                # 进程已经启动，直接返回监听的端口
                if isinstance(r, tuple):
                    web_process = r[0][r[1]]
                    port_group = re.search(r'--port=(\d+) --login=True',
                                           web_process)
                    if port_group:
                        port = int(port_group.group(1))
                        return (0, '', port)
                    else:
                        return (s, m, r)
                else:
                    # 调用 _get_console_port 获取所有进程的端口
                    s, m, r = self._get_console_port(
                        msg['id'],
                        msg['cid'],
                        msg['host'],
                        msg['username'],
                        r
                    )
                    # 创建进程
                    if s == 0:
                        port = r['free_ports'][0]
                        exec_id = self.connection.exec_create(
                            container=msg['cid'],
                            cmd=base_command % port,
                            tty=True,
                            stderr=False,
                            stdout=False
                        )['Id']
                        self.connection.exec_start(exec_id=exec_id,
                                                   detach=True,
                                                   tty=True)
                        return (0, '', port)
                    else:
                        return (s, m, r)
            else:
                return (s, m, r)

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
                    exec_id = self.connection.exec_create(
                        container=c_id,
                        cmd=c,
                        tty=True,
                        stderr=False,
                        stdout=False
                    )['Id']
                    self.connection.exec_start(
                        exec_id=exec_id,
                        detach=True,
                        tty=True
                    )
            # 检查进程是否成功启动
            if console:
                # 调用 _get_console_process 获取容器所有的 console 进程
                s, m, r = self._get_console_process(msg)
                if s == 0:
                    # 调用 _get_console_port 获取容器所有的 console 端口
                    process_info = self._get_console_port(
                        msg['id'],
                        c_id,
                        msg['host'],
                        msg['username'],
                        r
                    )
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

    def _get_console_process(self, msg, web_console=False):
        """获取所有 console 进程"""

        try:
            # 拿出容器所有的进程
            s, m, r = self.top_container(msg)
            if s == 0:
                processes = r['processes']
                processes_list = []
                # 保存结果到 processes_list 中
                for p in xrange(len(processes)):
                    process = processes[p][-1]
                    if 'butterfly.server.py' in process:
                        processes_list.append(process)
                    if web_console:
                        if 'buttonfly.server.py' and 'login=True' in process:
                            web_console_index = len(processes_list) - 1
                if 'web_console_index' in dir():
                    # 返回过滤的进程和 web_console 进程的索引
                    return (0, '', (processes_list, web_console_index))
                else:
                    # 只返回过滤的进程
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
        result = {
            'id': db_id,
            'cid': c_id,
            'host': host,
            'console': {},
            'use_ports': [],
            'free_ports': [],
            'username': username,
            'message_type': 'console_container'
        }

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
            base_command = "/pythonpie/.console/bin/butterfly.server.py \
--unsecure --host=0.0.0.0 --port=%s --login=False --cmd='%s'"

            # 调用 _get_console_process 获取容器所有的 console 进程
            status, message, result = self._get_console_process(msg)
            if status == 0:
                # 调用 _get_console_port 获取容器所有的 console 端口
                s, m, r = self._get_console_port(
                    db_id,
                    c_id,
                    msg['host'],
                    msg['username'],
                    result
                )
                if s == 0:
                    exist_command = r['console'].keys()
                    exec_command = simplejson.loads(msg['command'])
                    use_ports = r['use_ports']
                    free_ports = r['free_ports']
                    kill_ports = []
                    will_command = []
                    nginx_command = []
                    for i in xrange(len(exec_command)):
                        if '.' in exec_command[i]:
                            if exec_command[i].startswith('nginx') and \
                               exec_command[i].split('.')[-1] == 'html':
                                nginx_command.append(exec_command[i])
                                continue

                        if exec_command[i] not in exist_command:
                            try:
                                command = base_command % (free_ports[i],
                                                          exec_command[i])
                            except Exception, e:
                                command = base_command % (use_ports[0],
                                                          exec_command[i])
                                kill_ports.append(use_ports[0])
                                use_ports.pop(0)
                            will_command.append(command)

                    if kill_ports:
                        for port in kill_ports:
                            p = subprocess.Popen(["ps aux | awk \
                                '/\-\-port=%d \-\-login/ {print $2}'" % port],
                                                 stdout=subprocess.PIPE,
                                                 shell=True)
                            out, err = p.communicate()
                            pid = int(out.splitlines()[0].split(None, 1)[0])
                            os.kill(pid, signal.SIGKILL)

                    msg['console_command'] = will_command
                    s, m, r = self.exec_container(msg, console=True)
                    if nginx_command:
                        if s == 0:
                            s1, m1, r1 = self._get_port(db_id, c_id, 81)
                            if s1 == 0:
                                for c in nginx_command:
                                    r['console'][c] = {'private_port': 81,
                                                       'public_port': r1}
                                return (s, m, r)
                            else:
                                return (s1, m1, r1)
                        else:
                            return (s, m, r)
                    else:
                        return (s, m, r)
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
            new_msg = msg

            # Docker 容器在 Host 上的路径
            host_dir_path = os.path.join(self.container_path, c_id)

            # 遍历所有的文件
            for f in files:
                # 容器中的文件路径
                container_file_path = os.path.dirname(f)
                # 容器中的文件名字
                container_file_name = os.path.basename(f)
                # 文件所在 Host 上目录的完全路径
                full_path = host_dir_path + container_file_path
                # 文件所在 Host 上的完全路径
                full_file_path = os.path.join(full_path, container_file_name)

                # 如果 full_path 不存在, 就创建
                if not os.path.exists(full_path):
                    os.makedirs(full_path)

                # 写入数据到文件中
                fo = open(full_file_path, 'w')
                fo.writelines(files[f].encode('utf-8'))
                fo.close()

                s1, m1, r1 = self._link_file_to_nginx(f, new_msg)
                if s1 != 0:
                    return (s1, m1, r1)

            return (0, '', msg)
        except Exception, e:
            return (1, {'error': str(e), 'id': msg['id']}, '')

    def files_read_container(self, msg):
        """读取容器中文件的内容"""

        try:
            c_id = msg['cid']
            files = msg['files']
            new_msg = msg

            # Docker 容器在 Host 上的路径
            host_dir_path = os.path.join(self.container_path, c_id)

            files_content = {}
            # 遍历所有的文件
            for f in files:
                # 容器中的文件路径
                container_file_path = os.path.dirname(f)
                # 容器中的文件名字
                container_file_name = os.path.basename(f)
                # 文件所在 Host 上目录的完全路径
                full_path = host_dir_path + container_file_path
                # 文件所在 Host 上的完全路径
                full_file_path = os.path.join(full_path, container_file_name)

                # 如果 full_path 不存在, 就创建
                if not os.path.exists(full_path):
                    os.makedirs(full_path)

                # 如果文件不存在, 写入默认内容
                if not os.path.exists(full_file_path):
                    fo = open(full_file_path, 'w')
                    fo.writelines(files[f].encode('utf-8'))
                    fo.close()

                s, m, r = self._exec_file_content(msg['id'], c_id, f)
                files_content[f] = r

                s1, m1, r1 = self._link_file_to_nginx(f, new_msg)
                if s1 != 0:
                    return (s1, m1, r1)

            msg['files'] = files_content
            return (0, '', msg)

        except Exception, e:
            return (1, {'error': str(e), 'id': msg['id']}, '')

    def _exec_file_content(self, db_id, c_id, filename):
        """通过 Docker exec api 获取容器中文件内容"""

        try:
            exec_id = self.connection.exec_create(
                container=c_id,
                cmd='cat %s' % filename
            )['Id']
            content = self.connection.exec_start(exec_id=exec_id)
            return (0, '', content)
        except Exception, e:
            return (1, {'error': str(e), 'id': id}, '')

    def _link_file_to_nginx(self, f, new_msg):
        """判断文件类型, 如果是 html css js 文件则链接文件到 Ningx 中"""

        bash_command = []
        nginx_process = []
        host_dir_path = os.path.join(self.container_path, new_msg['cid'])
        if '.' in f:
            f_type = f.split('.')[-1]
            if f_type == 'html' or f_type == 'css' or f_type == 'js':
                f_path = os.path.dirname(f)
                f_name = os.path.basename(f)
                f_nginx_path = self.nginx_root + f_path
                f_host_dir_path = host_dir_path + f_nginx_path
                f_host_file_path = os.path.join(
                    f_host_dir_path,
                    f_name
                )

                if not os.path.exists(f_host_dir_path):
                    bash_command.insert(0,
                                        'mkdir -p %s' % f_nginx_path)

                if not os.path.exists(f_host_file_path):
                    bash_command.append('ln -sf %s %s' %
                                        (f, f_nginx_path))
                s, m, r = self.top_container(new_msg)
                if s == 0:
                    for p in r['processes']:
                        if 'nginx: worker process' in p:
                            nginx_process.append(p)
                else:
                    return (s, m, r)
        else:
            return (0, '', '')

        if not nginx_process:
            bash_command.append('service nginx start')

        if bash_command:
            new_msg['command'] = simplejson.dumps(bash_command)
            s, m, r = self.exec_container(new_msg, console=False)
            if s != 0:
                return (s, m, r)
        return (0, '', '')


def main(msg):
    """Containers 程序入口,
    用来传递 message 类型

    """
    msg_type = msg['message_type']
    exec_action = Container_Manager()
    return getattr(exec_action, msg_type)(msg)
