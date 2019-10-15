#!/usr/bin/env python
# coding=utf-8

import MySQLdb as mysql
from config import config

db_conf = config('xnet', 'db')


class LinkMysql(object):
    '''简单对mysqldb进行上下文封装
    操作完成后自动关闭连接
    '''

    def __init__(self):
        self.conn = mysql.connect(
            host=db_conf['host'],
            port=int(db_conf['port']),
            user=db_conf['user'],
            passwd=db_conf['passwd'],
            db=db_conf['db'],
            charset=db_conf['charset']
        )

        self.conn.autocommit(True)
        self.cursor = self.conn.cursor()

    def __enter__(self):
        return self.cursor

    def __exit__(self, exc_type, exc_value, traceback):
        # 关闭连接
        self.cursor.close()
        self.conn.close()
        # 如果使用过程发现了异常返回假，这样系统就会重新抛出异常
        if exc_type:
            return False
        return True


class db(object):
    '''定义了一些简单的操作方法
    restult 返回的是执行结果，比如添加了1条数据返回的就是1
    data 是查询的数据，返回的是元组形式
    '''
    @staticmethod
    def execute(sql, param=None):
        '''返回执行结果'''
        with LinkMysql() as db:
            result = db.execute(sql, param)
        return result

    @staticmethod
    def select(sql, param=None):
        '''返回元组，0是结果，1是数据'''
        with LinkMysql() as db:
            result = db.execute(sql, param)
            data = db.fetchall()
        return result, data


if __name__ == '__main__':
    '''简单使用方法'''
    # 插入
    #sql = "INSERT INTO `stat_0` (`host`,`mem_free`,`mem_usage`,`mem_total`,`load_avg`,`time`)VALUES('incloud_ma_sd', '6711', '1108', '7819', '0.0', '1435385887')"
    #data = db.execute(sql)
    #print data

    # 查询
    sql = "select * from stat_3 limit 1"
    data = db.select(sql)
    print data
