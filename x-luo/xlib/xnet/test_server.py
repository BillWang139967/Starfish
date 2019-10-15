#!/usr/bin/env python
# coding=utf-8

"""一个简单的 epoll 实现的网络协议
通过接收客户端的前 10 个字节，获取传输文件大小，然后进行处理

如果客户端发送 0000000002hi 服务端收到的就是 hi 然后进程处理后发送给客户端
"""
import snetbase
from snetframework import XNet

if __name__ == "__main__":
    def logic(in_data):
        print in_data
        return in_data[::-1]
    sock = snetbase.bind_socket("0.0.0.0", 9000)
    reverseD = XNet(sock, logic)
    reverseD.run()
