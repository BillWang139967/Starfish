# XNET

socket 使用 epoll 非阻塞，自定义传输协议，epoll 是注册回调函数，无需主动扫描 FD，长链接也只占用内存，性能更好

XNet 是异步通信

> 接受数据
```
# 先绑定个 socket
XNet(sock, transfer)      # 接收数据
```

> 发送数据
```
也可任意发多份给不同 server
send_data(host_l,data,sock_l,single_host_retry=3)
"""
  host_l is a list
  sock_l is a list
"""
```
