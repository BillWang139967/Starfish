#!/usr/bin/env python
# coding=utf-8
import os
import time
import fcntl
import socket
import struct
import signal
import threading
import subprocess


class Command(object):
    '''通过使用线程实现执行命令超时功能'''

    def __init__(self, cmd):
        self.cmd = cmd
        # 初始化信号处理方法 因为subprocess使用信号处理
        # 方式被引入的的时候别的包邮类似信号监听引起错误
        # SIGCHLD是程序执行完发出的信号 SIG_DFL是恢复默认行为
        signal.signal(signal.SIGCHLD, signal.SIG_DFL)

    def run(self, timeout):
        def target():
            self.process = subprocess.Popen(
                self.cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
            self.output, self.error = self.process.communicate()

        thread = threading.Thread(target=target)
        thread.start()
        thread.join(timeout)

        if thread.is_alive():
            self.process.kill()
            return (False, "timeout", self.process.pid)
        return (self.process.returncode, self.output, self.error)


def get_iphostname():
    '''获取linux主机名和第一个网卡IP地址'''
    def get_ip(ifname):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ipaddr = socket.inet_ntoa(fcntl.ioctl(
            sock.fileno(),
            0x8915,  # SIOCGIFADDR
            struct.pack('256s', ifname[:15])
        )[20:24]
        )
        sock.close()
        return ipaddr
    try:
        ip = get_ip('eth0')
    except IOError:
        ip = get_ip('eno1')
    hostname = socket.gethostname()
    return {'hostname': hostname, 'ip': ip}


if __name__ == "__main__":
    command = Command('ls')
    outdata = command.run(timeout=1)
    print outdata
    # ip_hostname
    #host_info  = get_iphostname()
    #print host_inf
