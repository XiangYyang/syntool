# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0

"""
Synthesize toolchain
~~~~~~~~~~~~~~~~~~

构建工具

  +------------------------------+
  |  Synthesize                   |
  |  文件名称: action.py          |
  |  文件作用: 动作                |
  |  创建日期: 2023-05-25         |
  |  开发人员: 向阳               |
  +------------------------------+

 Copyright (C) 向阳, all rights reserved.

"""

import re
import subprocess
from typing import List, Optional
from project import Project


class ActionBase:
    """
    带各个工具目录的action base
    """

    # vvp
    vvp_path: str

    # yosys
    yosys_path: str

    # iverilog
    iverilog_path: str

    def __init__(self, tool_basepath: Optional[str]):
        basepath: str
        if tool_basepath is not None:
            basepath = tool_basepath + '/'
        else:
            basepath = ''
        # 工具
        self.vvp_path = f'{basepath}vvp'
        self.yosys_path = f'{basepath}yosys'
        self.iverilog_path = f'{basepath}iverilog'


class Actions(ActionBase):
    """
    动作
    """

    def __init__(self, path: Optional[str]):
        super(Actions, self).__init__(path)

    def make_testbench(self, project: Project, module: str) -> bool:
        """
        构建test bench
        """
        print(f'> \033[1;36mmake_test {module}')
        if module not in project.files:
            # 不存在的模块
            print(f'  \033[1;31mModule "{module}" is not exist.')
            return False
        if module not in project.test_bench:
            # 不存在test bench
            print(
                f'  \033[1;31mTest bench for module "{module}" is not exist.')
            return False
        # 输出文件
        ivlg_mkout = f'{project.build_out_dir}{module}.vo'
        # 输入文件
        inp_file: List[str] = []
        inp_file.append(project.files[module].fullpath)
        inp_file.append(project.test_bench[module].fullpath)
        # 调用iverilog生成仿真
        return self._iverilog_invoke(project, ['-o', ivlg_mkout], inp_file)

    def synthesis(self, project: Project, output: str) -> bool:
        """
        综合
        """
        # 命令脚本
        command_script = []
        # 输入文件
        command_script += self._yosys_gen_load_script(project)
        # 进行综合
        command_script.append('synth')
        # 综合输出
        script = f'write_verilog {output}'
        command_script.append(script)
        # 执行
        script = '; '.join(command_script)
        return self._yosys_invoke(script)

    def _yosys_gen_load_script(self, project: Project) -> List[str]:
        """
        生成加载文件和设置顶层模块的脚本
        """
        # 命令脚本
        command_script = []
        # 输入文件
        for (module, file) in project.files.items():
            script = f'read_verilog {file.fullpath}'
            command_script.append(script)
        # 设置顶层模块
        script = f'hierarchy -check -top {project.top_module}'
        command_script.append(script)
        # ret
        return command_script

    def _yosys_invoke(self, script: str) -> bool:
        """
        调用yosys
        """
        # 执行
        command = [
            self.yosys_path,
            '-Q',
            '-v', 'info',
            '-p', script
        ]
        cmd_strs = ' '.join(command)
        print('>\033[1;36m Running yosys...')
        try:
            subprocess.run(command, check=True)
            return True
        except subprocess.CalledProcessError:
            print('> \033[1;31myosys exitcode is not 0.')
            print(f'  \033[1;31mCommand: {repr(cmd_strs)}')
        return False

    def _iverilog_invoke(self, project: Project, ext_args: List[str], file_args: List[str]) -> bool:
        """
        调用iverilog
        """
        command = [
            self.iverilog_path
        ]
        # 添加附加的参数
        command += ext_args
        # 添加including目录
        for including_dir in project.including_dir:
            command.append('-I')
            command.append(including_dir)
        # 添加库目录
        for lib in project.libs:
            command.append('-y')
            command.append(lib.full_path)
        # 添加IP核的RTL文件路径到搜索路径
        for (ip_name, ip_core) in project.ip_cores.items():
            command.append('-y')
            command.append(ip_core.root_dir)
        # 添加rtl根目录到搜索路径
        command.append('-y')
        command.append(project.root_dir)
        # 添加文件路径到iverilog
        command += file_args
        # 命令行
        cmd_strs = ' '.join(command)
        print('>\033[1;36m Running iverilog...')
        # 执行命令
        try:
            subprocess.run(command, check=True)
            return True
        except subprocess.CalledProcessError:
            print('> \033[1;31miverilog exitcode is not 0.')
            print(f'  \033[1;31mCommand: {repr(cmd_strs)}')
        return False


class EnviromentActions(ActionBase):
    """
    环境相关的动作
    """

    def __init__(self, path: Optional[str]):
        super(EnviromentActions, self).__init__(path)

    def check_iverilog_enviroment(self) -> bool:
        """
        检查 iverilog 环境
        """
        # 执行iverilog -v
        print('> \033[1;36miverilog -v')
        ivlg_ret = subprocess.run(
            [self.iverilog_path, '-v'], capture_output=True, encoding='utf-8')
        # 找到"Icarus Verilog version"字串, 后面的连续数字是版本
        reg_match = re.match(
            r'Icarus Verilog version ([0-9]+\.[0-9]+)', ivlg_ret.stdout, flags=0)
        if reg_match is None:
            print('  \033[1;31miverilog command output is not be recognized.')
            return False
        else:
            # 分割得到版本号
            match_res: re.Match[str] = reg_match
            iverilog_version = match_res.groups()[0]
            print(f'  iverilog version {iverilog_version}')
            return True

    def check_yosys_enviroment(self) -> bool:
        """
        检查 yosys 环境
        """
        # 执行yosys -v
        print('> \033[1;36myosys -V')
        std_out = subprocess.run(
            [self.yosys_path, '-V'], capture_output=True, encoding='utf-8')
        # 找到"Yosys"字串, 后面是版本
        reg_match = re.match(
            r'(Y|y)osys (([a-zA-Z0-9]|\.)+)', std_out.stdout, flags=0)
        if reg_match is None:
            print('  \033[1;31myosys command output is not be recognized.')
            return False
        else:
            # 分割得到版本号
            match_res: re.Match[str] = reg_match
            version = match_res.groups()[1]
            print(f'  yosys version {version}')
            return True
