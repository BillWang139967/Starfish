#!/usr/bin/env python
import random

def get_cpu():
    return random.randint(1,100)

class mon:
    def runAllGet(self):
        server={}
        server["hostname"] = "meetbill"
        server['CPU']=get_cpu()
        return server

if __name__ == "__main__":
    print mon().runAllGet()
