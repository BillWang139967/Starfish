#!/usr/bin/env python

import os
import sys
import importlib

from xlib import daemon

root_path = os.path.split(os.path.realpath(__file__))[0]
os.chdir(root_path)

module = ["agent","server"]

def usage():
    print "usage: run_daemon.py agent|server start|stop|restart|status"
    sys.exit(2)

def main():
    if len(sys.argv) != 3:
        usage()

    daemon_name = sys.argv[1]
    if daemon_name not in module:
        usage()

    pkg = importlib.import_module('handlers.{pkg_name}'.format(pkg_name=daemon_name))
    class MyDaemon(daemon.Daemon):
        def run(self):
            pkg.main()

    ######################################
    # edit this code
    cur_dir = os.getcwd()
    if not os.path.exists("{cur_dir}/run/".format(cur_dir=cur_dir)):
        os.makedirs("./run")

    if not os.path.exists("{cur_dir}/log/".format(cur_dir=cur_dir)):
        os.makedirs("./log")

    my_daemon = MyDaemon(
        pidfile="{cur_dir}/run/{daemon_name}.pid".format(cur_dir=cur_dir,daemon_name=daemon_name),
        stdout="{cur_dir}/log/{daemon_name}_stdout.log".format(cur_dir=cur_dir,daemon_name=daemon_name),
        stderr="{cur_dir}/log/{daemon_name}_stderr.log".format(cur_dir=cur_dir,daemon_name=daemon_name)
    )

    if 'start' == sys.argv[2]:
        my_daemon.start()
    elif 'stop' == sys.argv[2]:
        my_daemon.stop()
    elif 'restart' == sys.argv[2]:
        my_daemon.restart()
    elif 'status' == sys.argv[2]:
        alive = my_daemon.is_running()
        if alive:
            print('process [%s] is running ......' % my_daemon.get_pid())
        else:
            print('daemon process [%s] stopped' % daemon_name)
    else:
        print "Unknown command"
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
