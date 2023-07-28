# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0

"""
Synthesize toolchain
~~~~~~~~~~~~~~~~~~

构建工具

  +------------------------------+
  |  Synthesize                   |
  |  文件名称: __main__.py        |
  |  文件作用: __main__           |
  |  创建日期: 2022-06-22         |
  |  开发人员: 向阳               |
  +------------------------------+

 Copyright (C) 向阳, all rights reserved.

"""

# 版本
from app import app_start
import argparse
import colorama

version = '1.0.0'

# 欢迎信息
welcome_info = f"""Synthesize toolchain

Version {version}, Copyright (C) 向阳, all rights reserved.
"""


if __name__ == '__main__':
    colorama.init(autoreset=True)
    print(welcome_info)
    parser = argparse.ArgumentParser(description='综合工具')
    # 选项
    # 工程文件名
    parser.add_argument(
        '--project',
        type=str,
        default='./project.toml',
        help='工程文件, 默认为根目录下的"project.toml"'
    )
    # base path
    parser.add_argument(
        '--basepath',
        type=str,
        default=None,
        help='iverilog安装目录'
    )
    # 目标
    parser.add_argument(
        '--target',
        type=str,
        default=None,
        help='构建/仿真目标'
    )
    # 动作
    parser.add_argument('active', type=str, help='动作')

    args = parser.parse_args()

    app_start(args)
