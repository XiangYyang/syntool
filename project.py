# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0

"""
Synthesize toolchain
~~~~~~~~~~~~~~~~~~

构建工具

  +------------------------------+
  |  Synthesize                   |
  |  文件名称: project.py         |
  |  文件作用: 工程文件解析         |
  |  创建日期: 2022-06-22         |
  |  开发人员: 向阳               |
  +------------------------------+

 Copyright (C) 向阳, all rights reserved.

"""

import os
import re
import rtoml
from typing import Dict, Any, List, Callable
from pathlib import Path
from dataclasses import dataclass


@dataclass
class FileInfo:
    # 文件名(不包括后缀)
    filename: str

    # 文件后缀. 包括那个点
    ext_name: str

    # 完整路径
    fullpath: str


@dataclass
class IpCoreInfo:
    # 名称
    name: str

    # 根目录
    root_dir: str

    # 文件, 模块名 -> 文件信息
    rtl_files: Dict[str, FileInfo]


@dataclass
class LibInfo:
    # 名称
    name: str

    # 库路径
    full_path: str


class Project:
    """
    项目数据
    """

    # 项目语言
    language: str

    # 文件, 模块名 -> 文件信息
    files: Dict[str, FileInfo]

    # test_bench, 模块名 -> test bench文件信息
    test_bench: Dict[str, FileInfo]

    # ip核, ip核名称 -> ip核信息
    ip_cores: Dict[str, IpCoreInfo]

    # 库
    libs: List[LibInfo]

    # 包含目录
    including_dir: List[str]

    # RTL文件根目录
    root_dir: str

    # 顶层模块
    top_module: str

    # 构建输出目录, 带末尾的那个'/'
    build_out_dir: str

    def __init__(self, file: str):
        try:
            # 解析toml
            toml_dat = rtoml.load(Path(file))
            toml_prj_dat = toml_dat['project']
            self._load_project_properties(toml_prj_dat)
            # 遍历test bench文件
            # 测试文件名 -> 文件信息
            test_bench_file: Dict[str, FileInfo] = {}
            # 遍历添加文件
            self._file_lists(
                toml_prj_dat['tb_dir'],
                toml_prj_dat['tb_dir_pattern'],
                self._append_file_to_map_parteval(test_bench_file)
            )
            # 检查所有的rtl文件, 确认其有一个对应的test bench
            # 然后添加到tb文件列表
            self.test_bench = self._load_testbench_files(toml_prj_dat, test_bench_file)
            # ip核
            self.ip_cores: Dict[str, IpCoreInfo]
            if 'ip' in toml_dat:
                toml_ip_dat = toml_dat['ip']
                self.ip_cores = self._load_ip_cores(toml_ip_dat)
            else:
                self.ip_cores = {}
            # 额外的工程特定信息
            if 'spec' in toml_prj_dat:
                spec_file: str = toml_prj_dat['spec']
                (self.libs, ext_including) = self._load_spec_file(spec_file)
            else:
                (self.libs, ext_including) = ([], [])
            # 包含目录
            self.including_dir = []
            # 添加rtl源文件根目录作为including path
            self.including_dir.append(self.root_dir)
            # 添加ip核的rtl根目录作为including path
            for (ip_name, ip_core) in self.ip_cores.items():
                self.including_dir.append(ip_core.root_dir)
            # 额外的包含目录
            self.including_dir += ext_including
            # 构建输出目录
            self.build_out_dir = os.path.abspath(
                toml_prj_dat['build_dir']) + os.sep
            if not os.path.exists(self.build_out_dir):
                # 创建目录
                os.mkdir(self.build_out_dir)
        except KeyError:
            raise AttributeError('Project file was missing some items.')
        except FileNotFoundError as e:
            raise AttributeError(f'Missing file {e.filename}.')

    def _load_project_properties(self, toml_prj_dat):
        """
        加载工程的属性
        """
        self.language = toml_prj_dat['language']
        self.top_module = toml_prj_dat['top_module']
        self.root_dir = os.path.abspath(toml_prj_dat['rtl_dir'])
        # 遍历rtl文件夹下的内容, 加入文件列表
        self.files: Dict[str, FileInfo] = {}
        # 遍历添加文件
        self._file_lists(
            toml_prj_dat['rtl_dir'],
            toml_prj_dat['rtl_dir_pattern'],
            self._append_file_to_map_parteval(self.files)
        )
        # 检查顶层模块
        self._check_top_module()

    def _check_top_module(self):
        """
        检查顶层模块是存在的
        """
        if self.top_module not in self.files:
            print(
                f'  \033[1;31mTop module "{self.top_module}" is not exist.')
            raise Exception()

    def _load_testbench_files(self, toml_prj_dat, test_bench_files: Dict[str, FileInfo]) -> Dict[str, FileInfo]:
        """
        加载test bench文件到工程
        """
        test_bench: Dict[str, FileInfo] = {}
        for module_name, _file in self.files.items():
            tb_fmt = toml_prj_dat['tb_file_fmt']
            tb_module = tb_fmt.format(module_name)
            if tb_module in test_bench_files:
                # 存在于之前查找的tb文件中, 添加进去
                test_bench.update({module_name: test_bench_files[tb_module]})
        return test_bench

    def _load_ip_cores(self, toml_ip_dat) -> Dict[str, IpCoreInfo]:
        """
        加载IP核
        """
        ip_cores = {}
        for ip in toml_ip_dat:
            # ip核名称
            ip_name = ip['name']
            # 添加ip核的rtl文件
            ip_files: Dict[str, FileInfo] = {}
            self._file_lists(
                ip['rtl_dir'],
                ip['rtl_dir_pattern'],
                self._append_file_to_map_parteval(ip_files)
            )
            # 确认ip_name在里面是一个实实在在的模块
            if ip_name not in ip_files:
                print(
                    f'  \033[1;31mCannot find top module "{ip_name}" in IP core "{ip_name}".')
                raise Exception()
            # 添加到ip核的dict
            ip_info = IpCoreInfo(
                name=ip_name,
                root_dir=os.path.abspath(ip['rtl_dir']),
                rtl_files=ip_files
            )
            ip_cores.update({ip_name: ip_info})
        return ip_cores

    @staticmethod
    def _load_spec_file(file: str):
        """
        加载工程特化的描述文件
        """
        full_path = os.path.abspath(file)
        toml_dat = rtoml.load(Path(full_path))
        # 库信息
        libs = []
        if 'lib' in toml_dat:
            toml_lib_dat = toml_dat['lib']
            for lib in toml_lib_dat:
                lib_info = LibInfo(
                    name=lib['name'],
                    full_path=os.path.abspath(lib['path'])
                )
                libs.append(lib_info)
        # 包含目录
        including_dir = []
        if 'ext_including_dir' in toml_dat:
            for inc_dir in toml_dat['ext_including_dir']:
                including_dir.append(os.path.abspath(inc_dir))
        return (libs, including_dir)

    @staticmethod
    def _append_file_to_map_parteval(target_map: Dict[str, FileInfo]) -> Callable[[str, str, str], Any]:
        """
        返回把文件添加到target_map的函数
        """
        def impl(filename: str, filepath: str, extname: str):
            info = FileInfo(
                fullpath=filepath,
                ext_name=extname,
                filename=filename
            )
            # 添加到map
            if info.filename in target_map:
                print(
                    f'  \033[1;31mModule "{info.filename}" is already exist.')
                raise Exception()
            else:
                target_map.update({info.filename: info})

        return impl

    @staticmethod
    def _file_lists(dir: str, pattern: str, cont: Callable[[str, str, str], Any]):
        """
        遍历文件
        cont: 文件名, 文件完整路径, 文件拓展名 -> ()
        """
        regexp = re.compile(f'\\./{pattern}')
        # 遍历目录下所有内容
        for path, _dir, files in os.walk(dir):
            for file in files:
                fullpath = os.path.join(path, file)
                # 避免windows下'\\'
                # win下'\\'和'/'都是不合法的文件名, 所以可以替换
                fullpath_text = fullpath.replace('\\', '/')
                if regexp.match(fullpath_text):
                    # 文件符合要求
                    # 文件拓展名, 包括那个.
                    ext_name = os.path.splitext(fullpath)[1]
                    # 文件名, 不带后缀
                    file_name = os.path.basename(fullpath)[:-len(ext_name)]
                    # 返回
                    cont(file_name, os.path.abspath(fullpath), ext_name)
