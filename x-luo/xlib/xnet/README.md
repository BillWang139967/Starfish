# XNET

socket 使用 epoll 非阻塞，自定义传输协议，epoll 是注册回调函数，无需主动扫描 FD，长链接也只占用内存，性能更好

```
设定了一套通信的协议，以 10 个 byte 的 ASCII 码数字的头来表示，后续数据的长度，例如：

0000000008MEETBILL
0000000012hello world\n

这样做的好处在于，我们可以很容易的解析消息的结束位置。
```

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
