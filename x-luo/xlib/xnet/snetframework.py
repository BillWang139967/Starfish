#!/usr/bin/env python
# coding=utf-8

"""一个简单的 epoll 实现的网络协议
通过接收客户端的前 10 个字节，获取传输文件大小，然后进行处理
如果客户端发送 0000000002hi 服务端收到的就是 hi 然后进程处理
后发送给客户端

"""

import select
import socket
import logging

from snetbase import NetBase


class XNet(NetBase):
    '''Net 处理架构'''

    def __init__(self, sock, logic):
        # 继承父类 init
        super(XNet, self).__init__(sock, logic)
        # 自定义处理方法
        self.sm = {
            "accept": self.accept2read,
            "read": self.read2process,
            "write": self.write2read,
            "process": self.process,
            "closing": self.close,
        }

    def accept2read(self, fd):
        '''获取 socket，并使 socket 转换为 read 状态'''
        # 通过父类获取 socket 链接
        conn_addr = self.accept(fd)
        # 如果获取到的是 retry 就什么都不操作，让 epoll 判断进行再次读取
        # 如国获取到了 socket 对象，进行 epoll 注册，创建状态机
        # 并改变状态机状态为 read
        if not conn_addr == "retry":
            conn = conn_addr[0]
            addr = conn_addr[1]
            self.setFd(conn, addr)
            self.epoll_sock.register(conn.fileno(), select.EPOLLIN)
            logging.info(
                "***chang socket fd(%s) state to read***" %
                conn.fileno())
            self.conn_state[conn.fileno()].state = "read"
        else:
            pass

    def read2process(self, fd):
        '''处理 read 状态，并传入 proces 进行执行'''
        # 获取 read 状态
        try:
            read_ret = self.read(fd)
        except Exception as msg:
            # 发生错误后切换到 closing 状态
            read_ret = "closing"
        # 获取状态如果是 process 状态嗲用 process 进行处理
        # closing 状态关闭连接，如果其他状态不用处理，让 epoll 判担在次读取
        if read_ret == "process":
            self.process(fd)
        elif read_ret == "readcontent":
            pass
        elif read_ret == "readmore":
            pass
        elif read_ret == "retry":
            pass
        elif read_ret == "closing":
            self.conn_state[fd].state = 'closing'
            self.state_machine(fd)
        # 如果返回了其他问题，择抛出异常
        else:
            raise Exception("impossible state returned by self.read")

    def write2read(self, fd):
        '''使用 write 发送 process 处理的数据
        处理完后返回 read 状态继续监听客户端发送'''
        try:
            write_ret = self.write(fd)
        except socket.error as msg:
            write_ret = "closing"

        if write_ret == "writemore":
            pass
        # 如果已经发送完成调整为 read 状态，改变 epoll 为监听状态继续监听
        elif write_ret == "writecomplete":
            sock_state = self.conn_state[fd]
            conn = sock_state.sock_obj
            addr = sock_state.sock_addr
            self.setFd(conn, addr)
            logging.info("***chang socket fd(%s) state to read***" % fd)
            self.conn_state[fd].state = "read"
            self.epoll_sock.modify(fd, select.EPOLLIN)
        elif write_ret == "closing":
            self.conn_state[fd].state = 'closing'
            self.state_machine(fd)
        else:
            raise Exception("impossible state returned by self.write")


if __name__ == "__main__":
    import snetbase
    '''反转测试'''
    def logic(in_data):
        return in_data[::-1]
    '''多进程启动
    sock = bind_socket("0.0.0.0", 9000)
    fork_processes(0)
    reverseD = xNet(sock, logic)
    reverseD.run()
    '''

    '''单进程启动'''
    sock = snetbase.bind_socket("0.0.0.0", 9000)
    reverseD = XNet(sock, logic)
    reverseD.run()
