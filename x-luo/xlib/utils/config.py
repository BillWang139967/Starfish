# coding=utf-8

import ConfigParser

# 当前工作目录的绝对路径
# work_path = os.path.dirname(os.path.realpath(__file__))


def config(conf_path, conf_file, conf_name=None):
    '''
    conf_path: 配置文件路径
    conf_file: 配置文件的名称
    conf_name: 配置文件中项目的名称,如果为空择显示文件中有哪些配置名称
    '''
    # 使用ConfigParser读取ini配置文件
    cf = ConfigParser.ConfigParser()
    # 在构造对象之后设置 optionxform 属性为 str 即可区别保留大小写
    cf.optionxform = str
    # 获取配置文件路径
    conf_file = "%s/%s" % (conf_path, conf_file)
    # cls表示自身类这里也就是config
    cf.read(conf_file)
    if conf_name:
        # 获取数据的项目的数据
        conf = cf.items(conf_name)
        return dict(conf)
    # 获取配置文件中有哪些项目
    return cf.sections()


if __name__ == "__main__":
    import os
    # 当前工作目录的绝对路径
    work_path = os.path.dirname(os.path.realpath(__file__))
    conf_path = "{work_path}/../../server/config".format(work_path=work_path)

    # 显示有哪些 section
    print config(conf_path,"x-luo")

    # 获取对应 section
    f = config(conf_path,"x-luo", "server")
    print f
