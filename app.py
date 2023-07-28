# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0

"""
Synthesize toolchain
~~~~~~~~~~~~~~~~~~

构建工具

  +------------------------------+
  |  Synthesize                   |
  |  文件名称: app.py             |
  |  文件作用: 应用程序            |
  |  创建日期: 2022-06-22         |
  |  开发人员: 向阳               |
  +------------------------------+

 Copyright (C) 向阳, all rights reserved.

"""

import rtoml
import subprocess
from argparse import Namespace
from action import Actions, EnviromentActions
from project import Project


def _load_project(prj_file: str) -> Project:
    """
    载入工程
    """
    print(f'> \033[1;36mload project: {prj_file}')
    prj = Project(prj_file)
    # 工程信息
    print('  language: \033[1;33m' + prj.language)
    print('  top module: \033[1;33m' + prj.top_module)
    print(f'  found \033[1;33m{len(prj.files)}\033[0m RTL file(s)')
    print(
        f'  found \033[1;33m{len(prj.test_bench)}\033[0m RTL TestBench file(s)')
    print(f'  found \033[1;33m{len(prj.ip_cores)}\033[0m IP core(s)')
    #
    return prj


def _check_enviroment(action: EnviromentActions, project_file: str) -> bool:
    """
    检查环境
    """
    try:
        # 检查iverilog
        action.check_iverilog_enviroment()
        # 检查yosys
        action.check_yosys_enviroment()
        # 检查工程文件是否合法
        _load_project(project_file)
        return True
    except FileNotFoundError:
        print(
            '  \033[1;31mTools was not found, did your forget add it to PATH?')
    except rtoml.TomlParsingError as e:
        print(f'  \033[1;31mProject file is invaild: {e}')
    except AttributeError as e:
        print(f'  \033[1;31mProject file missing one or more keys: {e}')
    except Exception as e:
        print(f'  \033[1;31mLoading project cause an exception: {e}')
    return False


def _make_simu(action: Actions, project_file: str, top_module: str) -> bool:
    """
    构建仿真文件
    """
    # 载入工程
    prj = _load_project(project_file)
    # 构建
    return action.make_testbench(prj, top_module)


def _dump_wave(action: Actions, prj: Project, top_module: str) -> bool:
    """
    构建波形输出
    """
    vvp = action.vvp_path
    # 仿真输出
    ivlg_mkout = f'{prj.build_out_dir}{top_module}.vo'
    print('>\033[1;36m Running vvp...')
    subprocess.run([vvp, '-n', ivlg_mkout], check=True)
    return True


def _simu(action: Actions, project_file: str, top_module: str) -> bool:
    """
    进行仿真
    """
    # 载入工程
    prj = _load_project(project_file)
    # 构建
    if not action.make_testbench(prj, top_module):
        return False
    # 仿真
    return _dump_wave(action, prj, top_module)


def _synth(action: Actions, project_file: str, output: str) -> bool:
    """
    进行综合
    """
    # 载入工程
    prj = _load_project(project_file)
    # 综合
    return action.synthesis(prj, output)


def app_start(args: Namespace):
    """
    启动应用程序
    """
    project: str = args.project
    prj_action = Actions(args.basepath)
    env_action = EnviromentActions(args.basepath)
    # 支持的动作
    active = {
        'check': lambda: _check_enviroment(env_action, project),
        'simu': lambda: _simu(prj_action, project, args.target),
        'synth': lambda: _synth(prj_action, project, args.target),
        'make_simu': lambda: _make_simu(prj_action, project, args.target),
    }
    res = False
    if args.active in active:
        res = active[args.active]()
    else:
        print(f'> \033[1;31mBuild action "{args.active}" is invaild.')
    # 检查情况
    if res:
        print(
            f'> \033[1;36mMake target "{args.target}" (action="{args.active}") successed.')
    else:
        print(
            f'> \033[1;31mMake target "{args.target}" (action="{args.active}") failed.')
        exit(-1)
