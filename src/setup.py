"""
A 1.5d hack-and-slash game.
Copyright (C) 2023  Lyx Huston

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or any
later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

sets up the cython compilation

A note on build directories:
The build directory that is made by Cython is already set to be ignored in .gitignore
"""

# use from command line: python setup.py build_ext --build-lib build/pyd
# keeps the

import os

from setuptools import setup
from setuptools.extension import Extension

from Cython.Build import cythonize
from Cython.Distutils import build_ext
from Cython.Compiler import Options

# these files had some sort of issue with compiling in Cython
# (currently 1, it was an issue with default arguments)
with open("exclude_from_cython_compile.txt", "r") as exclude_file:
    exclude = [line.strip().split("\\")[-1] for line in exclude_file.readlines()]

dirs = {"data", "general_use", "run_game", "screens"}
# attempt to put it all in one .pyd
# source_list = ["main.py"]
# for dir_name in dirs:
#     source_list.extend(
#         f"{dir_name}/{file_name}" for file_name in os.listdir(dir_name)
#         if file_name.endswith(".py") and file_name not in exclude
#     )
# extension_list = [Extension("main", source_list)]
# works in pycharm testing environment, nowhere else

# attempt to put directories into singular pyd-s
# org_list = [("main", ["main.py"])]
# for dir_name in dirs:
#     org_list.append((dir_name, [
#         f"{dir_name}/{file_name}" for file_name in os.listdir(dir_name)
#         if file_name.endswith(".py") and file_name not in exclude
#     ]))
# extension_list = [Extension(name, source_list) for name, source_list in org_list]
# works in pycharm testing environment, nowhere else

# attempt to make each file into a .pyd
extension_list = [Extension("main", ["main.py"])]
for dir_name in dirs:
    extension_list.extend(
        Extension(f"{dir_name}.{file_name.split('.')[0].replace('/', '.')}", [f"{dir_name}/{file_name.strip()}"])
        for file_name in os.listdir(dir_name)
        if file_name.strip() not in exclude and file_name.endswith(".py")
    )
# works everywhere

Options.docstrings = False

setup(
    name="DownTheLine",
    ext_modules=cythonize(extension_list,
        build_dir="build/c",
        compiler_directives={
            'language_level': "3",
            'always_allow_keywords': True
        }
    ),
    cmdclass=dict(
        build_ext=build_ext
    )
)

