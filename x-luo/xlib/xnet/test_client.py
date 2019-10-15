#!/usr/bin/env python
# coding=utf-8

import json

from cnetutil import send_data

if __name__ == "__main__":
    trans_l = ['127.0.0.1:9000']
    # agent socket使用列表，具体参考 sendData_mh
    agent_sock_l = [None]
    data = {"hostname": "meetbill"}
    # 发送给传输层
    send_data(trans_l, json.dumps(data), agent_sock_l)
