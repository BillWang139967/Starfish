#!/usr/bin/python
import Queue
import threading
import time
import json
from moniItems import mon

from xlib.utils.config import config
from xlib.xnet.cnetutil import send_data

agent_conf = config('./conf','agent', 'global')


class porterThread (threading.Thread):
    def __init__(self, name, q, ql, interval=None):
        threading.Thread.__init__(self)
        self.name = name
        self.q = q
        self.setDaemon(1)
        self.queueLock = ql
        self.interval = interval

    def run(self):
        #print "Starting %s"  % self.name
        if self.name == 'collect':
            self.put_data()
        elif self.name == 'sendjson':
            self.get_data()

    def put_data(self):
        m = mon()
        atime = int(time.time())
        while True:
            data = m.runAllGet()
            #print "put_data:",data
            self.queueLock.acquire()
            self.q.put(data)
            self.queueLock.release()
            btime = int(time.time())
            #print '%s  %s' % (str(data), self.interval-((btime-atime)%30))
            time.sleep(self.interval - ((btime - atime) % self.interval))

    def get_data(self):
        try:
            trans_l = agent_conf['trans_l'].split(';')
            print trans_l
            agent_sock_l = [None]
        except BaseException:
            pass
        while True:
            self.queueLock.acquire()
            if not self.q.empty():
                data = self.q.get()
                #print "get:",data
                send_data(trans_l, json.dumps(data), agent_sock_l)
            self.queueLock.release()
            time.sleep(self.interval)


def main():
    q1 = Queue.Queue(10)
    ql1 = threading.Lock()
    collect = porterThread('collect', q1, ql1, interval=3)
    collect.start()
    time.sleep(0.5)
    sendjson = porterThread('sendjson', q1, ql1, interval=3)
    sendjson.start()

    #print  "start"
    collect.join()
    sendjson.join()


if __name__ == "__main__":
    main()
