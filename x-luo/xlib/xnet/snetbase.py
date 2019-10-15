#!/usr/bin/env python
# coding=utf-8

"""一个简单的 epoll 实现的网络协议，这个模块定义了一些基础方法
通过接收客户端的前 10 个字节，获取传输文件大小，然后进行处理

如果客户端发送 0000000002hi 服务端收到的就是 hi
然后进程处理后发送给客户端
"""
import os
import sys
import time
import errno
import socket
import select
import multiprocessing
import logging


class STATE(object):
    """状态机状态"""

    def __init__(self):
        self.state = 'accept'
        # 需要读取的字节数
        self.need_read = 10
        self.need_write = 0
        # 已经收到的字节数
        self.have_read = 0
        self.have_write = 0
        # 读写缓存
        self.buff_read = ""
        self.buff_write = ""
        # socket 对象
        self.sock_obj = ""
        # 客户端连接 IP
        self.sock_addr = ""
        # 以下使用 check_fd 时才有效
        # 读取开始时间
        self.read_stime = None
        # 默认 read 等待最大超时时间
        self.read_itime = 30

    def state_log(self):
        '''dbug 显示每个 f 状态'''
        msg = (
            '\n current_fd:{fd} \n state:{state}'
            '\n need_read:{need_read} \n need_write:{need_write}'
            '\n have_read:{have_read}\n have_write:{have_write}'
            '\n buff_read:{buff_read} \n buff_write:{buff_write}'
            '\n sock_obj:{sock_obj} \n sock_addr:{sock_addr}'
        ) .format(
            fd=self.sock_obj.fileno(), state=self.state,
            need_read=self.need_read, need_write=self.need_write,
            have_read=self.have_read, have_write=self.have_write,
            buff_read=self.buff_read, buff_write=self.buff_write,
            sock_obj=self.sock_obj, sock_addr=self.sock_addr
        )
        logging.debug(msg)


def bind_socket(addr, port):
    '''生成监听的 socket'''
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((addr, port))
    sock.listen(10)
    return sock


class NetBase(object):
    '''无阻塞网络框架
    一些基础方法，方便复用
    '''

    def __init__(self, sock, logic):
        '''初始化对象'''
        # 链接状态字典，每个链接根据 socket 连接符建立一个字典，字典中链接状态机
        self.conn_state = {}
        logging.info("init: init listen socket ")
        # 使用 setFD 将监听 socket 链接符存入状态机中
        self.setFd(sock)
        # 新建 epoll 事件对象，后续要监控的事件添加到其中
        self.epoll_sock = select.epoll()
        # 第一个参数向 epoll 句柄中注册监听 socket 的可读事件（这个 fd 用于监听）
        # 第二个实用的是一个 epoll 的事件掩码 EPOLLIN 默认是只读
        self.epoll_sock.register(sock.fileno(), select.EPOLLIN)
        # 处理绑定方法
        self.logic = logic

    def setFd(self, sock, addr=None):
        '''创建状态机初始化状态
        STATE() 是初始状态，具体参考 STATE 类
        conn_state 是一个自定义的字典，用于存取每个 fd 的状态
        '''
        logging.info("setFD: crete init state")
        # 创建初始化状态
        tmp_state = STATE()
        tmp_state.sock_obj = sock
        tmp_state.sock_addr = addr
        # conn_states 是这字典使用 soket 连接符（这个 fileno 获取 socket 连接符，是个整数）做 key 链接状态机
        self.conn_state[sock.fileno()] = tmp_state
        # 将初始化状态记录到日志中
        self.conn_state[sock.fileno()].state_log()

    def state_machine(self, fd):
        '''跟据状态机切换状态执行不同方法
        sm 是一个 python 下的 switch 使用字典（需要自定义）
        如{'x':func0, "y":func1}, 使用不同的 key 执行不同的函数
        '''
        logging.info("state_machine: run state")
        # 取出 fd 状态字典
        sock_state = self.conn_state[fd]
        # 记录执行前状态
        sock_state.state_log()
        # 根据 fd 不同状态执行不同方法
        self.sm[sock_state.state](fd)

    def accept(self, fd):
        '''accpet 使用 epoll 等待检测客户端连接
        返回一个新的 socket 非阻塞对象
        '''
        logging.info("accept: accept client")
        try:
            # 取出 fd（这里是监听的的那个 fd）
            sock_state = self.conn_state[fd]
            # 取出 sock（取出监听的 soket）
            sock = sock_state.sock_obj
            # 使用 accept 方法为新进请求连接的连接，返回一个元组 conn 是一个新的 socket 连接，addr 是连接的客户端地址
            conn, addr = sock.accept()
            # 设置 socket 为非阻塞
            conn.setblocking(0)
            # 返回新链接进来的 socket 对象，和连接 IP 地址
            logging.info("accept: find new socket client fd(%s)" % conn.fileno())
            return conn, addr[0]
        except socket.error as msg:
            # EAGIIN 防止缓冲区满了等错误，这两个错误发生后 (erron 代码是 11)
            # ECONNABORTED 防止 TCP 链接三次握手后再次发送 RST(erron 代码是 103)
            # 再次运行 accept 返回重试状态 retry
            if msg.errno in (11, 103):
                return "retry"

    def read(self, fd):
        '''读取数据 (appcet 执行完后，切换到 read 状态）
        这里逻辑是这样的 先读 10 个字节头 根据 10 个字节头算出要接受数据的大小
        然后在次进行读，一直到读完后返回状态 process
        '''
        logging.info("read: start read data")
        # 根据传入的 fd 取出 socket
        sock_state = self.conn_state[fd]
        conn = sock_state.sock_obj
        try:
            # 判断需要读的字节数是不是小于等于 0, 比如客户端发送了 10 个 0 过来（状态机里面的 need_read)
            if sock_state.need_read <= 0:
                # 如果小于等于 0 关闭链接将状态机切换到 closing 并执行状态机
                # 或者直接抛出异常让异常处理关闭连接
                raise socket.error

            # 进行读取（使用 recv), 因为非阻塞 socket 会发生 socket 11 错误（如缓冲
            # 区读满）下面异常会处理
            one_read = conn.recv(sock_state.need_read)
            # 如果读取的结果为 0 有两种情况
            # 1 如 epoll 判断有数据需要接受但数据也没有发过来（如 tcp 校验失败）
            # 2 客户端关闭，tcp 也会发送一个空 FIN 文件过来（如果这种情况下不关闭会有问题
            # 应为客户端关闭了，epoll 没有关闭信号，如果没有关闭连接进行处理，epoll 会认为
            # 这个事件没有处理，一直需要读这里就会一直读死循环，造成 cpu 100%)
            if len(one_read) == 0:
                raise socket.error

            logging.info("read: read state")
            # 将收到的数据存入 buff
            sock_state.buff_read += one_read
            # 修改已经接受的字节数
            sock_state.have_read += len(one_read)
            # 修改还需要读取的字结数
            sock_state.need_read -= len(one_read)
            # 读取状态记录到日志
            sock_state.state_log()

            # 先处理前 10 个协议头
            if sock_state.have_read == 10:
                logging.info("read: protocol read end")
                # 判断读取前十个字节是否是数字
                # 如果不是数字抛出 socket.error 异常，产生这个异常后后面的异常处理就会关闭连接
                if not sock_state.buff_read.isdigit():
                    raise socket.error
                # 假如读取的数小于 0 抛出 socket.error 异常，产生这个异常后后面的异常处理就会关闭连接
                elif int(sock_state.buff_read) <= 0:
                    raise socket.error
                # 计算下次需要读取的大小
                sock_state.need_read += int(sock_state.buff_read)
                # 清空缓存
                sock_state.buff_read = ''
                # 协议读取完后的状态记录到日志
                sock_state.state_log()
                # 读取完完毕后读取内内容
                return "readcontent"

            # 如果 need_read 等于 0 说明已经读取完毕，可以执行 process 进行处理了
            elif sock_state.need_read == 0:
                # 读取完毕了返回 process 进行处理
                logging.info("read: read end")
                return "process"
            else:
                # 如果都不符合说明没有读取完继续读取
                return "readmore"

        except socket.error as msg:
            # 这里发生错误如客户端断开连接等要将状态及状态调整为 cloing，关闭连接
            # 要单独处理 socket 11 错误时由于比如用户发送的 10 个字节头，但是后面没
            # 有数据停顿了还没有发过来，就会发生这种错误，还有就是非阻塞 socket 时，
            # 若读不到数据就会报这个错误，所以不需要特别处理
            if msg.errno == 11:
                # 发生这个错误继续读
                return "retry"
            # 其他错误则返回关闭状态
            logging.info("***read: soket fd(%s) error(%s) "
                       "change state to closing***" % (fd, msg))
            return "closing"

    def process(self, fd):
        '''程序处方法使用传入的 logic 方法进行处理'''
        logging.info("proces: proces start")
        # 读取 socket
        sock_state = self.conn_state[fd]
        # 获取输入
        response = self.logic(sock_state.buff_read)
        # 将获取的输入的字符串获取到后进行拼接写入 buff_write
        sock_state.buff_write = "%010d%s" % (len(response), response)
        # 统计发送字节数
        sock_state.need_write = len(sock_state.buff_write)
        # 改变状态机状态
        sock_state.state = "write"
        # 改变 epoll 状态为写状态，改变后 epoll 会收到写信号 epoll 检测到后，会自动执行状
        # 态机不用手动切换
        self.epoll_sock.modify(fd, select.EPOLLOUT)
        # 执行完成记录状态机状态
        logging.info("***process: process end fd state change to write***")
        sock_state.state_log()

    def write(self, fd):
        '''wirte 用与在"process"处理完数据后向客户端返回数据'''
        logging.info("write: start write data")
        # 取出 socket
        sock_state = self.conn_state[fd]
        conn = sock_state.sock_obj
        # 定义发送从第几个字节开始
        last_have_send = sock_state.have_write
        try:
            logging.info("write: write state")
            # 取出发送数据 conn.send 会返回发送的字节数
            have_send = conn.send(sock_state.buff_write[last_have_send:])
            # 统计已经发送的字节
            sock_state.have_write += have_send
            # 计算出还需要发送的字节
            sock_state.need_write -= have_send
            # 日志记录发送状态
            sock_state.state_log()
            # 判断如果所有数据已经发送完了， 并且已经有发送的字节数
            if sock_state.need_write == 0 and sock_state.have_write != 0:
                # 说明已经发送完成
                logging.info("wirte: write end")
                return "writecomplete"
            else:
                # 如果错误，说明还没有发送完成继续发送
                return "readmore"

        except socket.error as msg:
            # 在 send 发送数据时如果 socket 缓冲区满了 epoll 会进入阻塞模式等待再次发送
            # 所以产生这个错的的时候 [Errno 11] Resource temporarily unavailable
            # 不需要处理，继续发送就好
            if msg.errno == 11:
                return "retry"
            logging.info(
                "***wirte: soket fd(%s) error(%s) change state to closing***" %
                (fd, msg))
            return "closing"

    def close(self, fd):
        '''关闭连接
        '''
        logging.info("close: close fd(%s)" % fd)
        '''取消 epoll 注册，一定要先取消 epoll 注册，在关闭连接
        因为 epoll 运行过快，会发生 socket 关闭，epoll 还没取消注册又收到信号的情况'''
        self.epoll_sock.unregister(fd)
        # 关闭 sock
        sock = self.conn_state[fd].sock_obj
        sock.close()
        # 从链接字典中删除这个 fd
        self.conn_state.pop(fd)

    def run(self):
        '''运行程序
        监听 epoll 是否有新连接过来
        '''
        while True:
            # epoll 对象哪些套接字在最近一次查询后又有新的需要注册的事件到来，然后根据状态及状态进行执行
            # 如果没有对象过来，epoll 就会阻塞在这里
            epoll_list = self.epoll_sock.poll()
            for fd, events in epoll_list:
                logging.info("epoll: epoll find fd(%s) have signal" % fd)
                sock_state = self.conn_state[fd]
                # 确认 epoll 状态如果有 io 事件 epoll hang 住则关闭连接
                if select.EPOLLHUP & events:
                    sock_state.state = "closing"
                # 如果 IO 时间 epoll 发生错误也关闭连接
                elif select.EPOLLERR & events:
                    sock_state.state = "closing"
                logging.info("epoll: use state_machine process fd(%s)" % fd)
                self.state_machine(fd)

    def check_fd(self):
        '''检查 fd 超时
        如果 read 指定时间呢没有读取到数据择关闭连接
        需要单独起一个线程进行监控
        '''
        while True:
            for fd in self.conn_state.keys():
                sock_state = self.conn_state[fd]
                # fd 是 read 状态并且 read_time 是真的
                # 判断该 fd 的 epoll 收到数据的等待时间是否超过间隔时间
                if sock_state.state == "read" and sock_state.read_stime \
                        and (time.time() - sock_state.read_stime) >= sock_state.read_itime:
                    # 超过定时器时间关闭该 fd
                    sock_state.state = "closing"
                    self.state_machine(fd)
            # 超时检查时间
            time.sleep(60)


def fork_processes(num_processes, max_restarts=100):
    '''多进程启动
    两个参数
    1 开启进程数，如果小于等于 0 则按 cpu 核心数开启
    2 子进程最大重启次数
    '''
    #   计算 CPU 核心数
    if num_processes is None or num_processes <= 0:
        num_processes = multiprocessing.cpu_count()
    # 字典以 pid 为 key 进程数位值
    children = {}

    # 创建子进程
    def start_child(i):
        # i 是运行的进程数
        pid = os.fork()
        if pid == 0:
            return i
        else:
            # 父进程将子进程 pid 存入字典
            children[pid] = i
            return None

    # 根据进程数量启动进程并返回进程 pid
    for i in range(num_processes):
        id = start_child(i)
        # 父进程运行到这里因为返回的是个空的所以会继续运行下面的代码
        # 子进程运行到这里因为程序已经运行完所以会结束运行
        if id is not None:
            return id
    # 父进程会继续运行下面
    # 子进程重启计数开始
    num_restarts = 0

    while children:
        try:
            # 等待子进程结束 os.wait() 回收
            pid, status = os.wait()
        except OSError as e:
            # 如果系统 EINTR 错误（信号中断）跳出继续进行循环
            if e.errno == errno.EINTR:
                continue
            # 其他 OS 错误则抛出
            raise
        # 如果子进程 pid 不再启动的进程里面跳出继续进循环
        if pid not in children:
            continue
        # 进程结束后从字典中删除，并返回事第几个进程
        id = children.pop(pid)
        # 可以根据不同状态计入日志
        # 如果进程由于信号而退出，则返回 True，否则返回 False
        if os.WIFSIGNALED(status):
            pass
        # 如果 WIFEXITED(status) 返回 True，WEXITSTATUS(status) 则返回一个整数，该整数是 exit() 调用的参数。否则返回值是未定义的
        elif os.WEXITSTATUS(status) != 0:
            pass
        # 其他错误跳出这次循环继续程序
        else:
            continue
        # 子进程最多的重启次数，如果子进程重启次数超过最大的设置则抛出异常
        num_restarts += 1
        if num_restarts > max_restarts:
            raise RuntimeError("Too many child restarts, giving up")
        # 正常情况下这个 id 已经退出了，我们在 fork 出一个新的进程
        new_id = start_child(id)
        # 如果 fork 成功了直接 return 退出这个子进程
        if new_id is not None:
            return new_id
    # 如果没有正常启动进程，子进程字典为空则退出进程
    sys.exit(0)
