#!/usr/bin/env python
# coding=utf-8

import json
import logging

from xlib.utils.config import config
from xlib.xnet.snetframework import XNet
from xlib.xnet.snetbase import bind_socket

import xlib.blog

xlib.blog.init_log("./log/xnet")

# 导入配置文件
trans_conf = config('./conf','server', 'server')

# 处理程序
def logic(data):
    # 打印接收到的数据
    #print data
    f1 = open('/tmp/test.txt','a')
    f1.write(data)
    f1.write('\n')
    f1.close()
    data = json.loads(data)
    return("OK")

def main():
    # 监听地址和端口
    addr = trans_conf['addr']
    port = int(trans_conf['port'])

    # 启动服务
    sock = bind_socket(addr, port)
    transD = XNet(sock, logic)
    transD.run()
if __name__ == '__main__':
    main()
