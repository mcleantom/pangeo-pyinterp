# Copyright (c) 2022 CNES
#
# All rights reserved. Use of this source code is governed by a
# BSD-style license that can be found in the LICENSE file.
"""This script is the entry point for building, distributing and installing
this module using distutils/setuptools."""
import datetime
import os
import pathlib
import platform
import re
import shlex
import subprocess
import sys
import sysconfig
from typing import ClassVar, Optional

import setuptools
import setuptools.command.build_ext
import setuptools.command.install
import setuptools.command.sdist
import setuptools.command.test

# Must be imported after setuptools for now (distutils is deprecated, but
# handles the build command for the moment).
import distutils.command.build  # isort: skip

# Check Python requirement
MAJOR = sys.version_info[0]
MINOR = sys.version_info[1]
if not (MAJOR >= 3 and MINOR >= 6):
    raise RuntimeError("Python %d.%d is not supported, "
                       "you need at least Python 3.6." % (MAJOR, MINOR))

# Working directory
WORKING_DIRECTORY = pathlib.Path(__file__).parent.absolute()

# OSX deployment target
OSX_DEPLOYMENT_TARGET = '10.14'


def build_dirname(extname=None):
    """Returns the name of the build directory"""
    extname = '' if extname is None else os.sep.join(extname.split(".")[:-1])
    return pathlib.Path(
        WORKING_DIRECTORY, "build",
        "lib.%s-%d.%d" % (sysconfig.get_platform(), MAJOR, MINOR), extname)


def execute(cmd):
    """Executes a command and returns the lines displayed on the standard
    output"""
    process = subprocess.Popen(cmd,
                               shell=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    assert process.stdout is not None
    return process.stdout.read().decode()


def update_meta(path, version):
    """Updating the version number description in conda/meta.yaml."""
    with open(path, "r") as stream:
        lines = stream.readlines()
    pattern = re.compile(r'{% set version = ".*" %}')

    for idx, line in enumerate(lines):
        match = pattern.search(line)
        if match is not None:
            lines[idx] = '{%% set version = "%s" %%}\n' % version

    with open(path, "w") as stream:
        stream.write("".join(lines))


def update_environment(path, version):
    """Updating the version number desciption in conda environment"""
    with open(path, 'r') as stream:
        lines = stream.readlines()
    pattern = re.compile(r'(\s+-\s+pyinterp)\s*>=\s*(.+)')

    for idx, line in enumerate(lines):
        match = pattern.search(line)
        if match is not None:
            lines[idx] = "%s>=%s\n" % (match.group(1), version)

    with open(path, "w") as stream:
        stream.write("".join(lines))


def revision():
    """Returns the software version"""
    os.chdir(WORKING_DIRECTORY)
    module = pathlib.Path(WORKING_DIRECTORY, 'src', 'pyinterp', 'version.py')

    # If the ".git" directory exists, this function is executed in the
    # development environment, otherwise it's a release.
    if not pathlib.Path(WORKING_DIRECTORY, '.git').exists():
        pattern = re.compile(r'return "(\d+\.\d+\.\d+)"')
        with open(module, "r") as stream:
            for line in stream:
                match = pattern.search(line)
                if match:
                    return match.group(1)
        raise AssertionError()

    stdout = execute("git describe --tags --dirty --long --always").strip()
    pattern = re.compile(r'([\w\d\.]+)-(\d+)-g([\w\d]+)(?:-(dirty))?')
    match = pattern.search(stdout)
    if match is None:
        # No tag found, use the last commit
        pattern = re.compile(r'([\w\d]+)(?:-(dirty))?')
        match = pattern.search(stdout)
        assert match is not None, f"Unable to parse git output {stdout!r}"
        version = "0.0"
        sha1 = match.group(1)
    else:
        version = match.group(1)
        commits = int(match.group(2))
        sha1 = match.group(3)
        if commits != 0:
            version += f".dev{commits}"

    stdout = execute("git log  %s -1 --format=\"%%H %%at\"" % sha1)
    stdout = stdout.strip().split()
    date = datetime.datetime.utcfromtimestamp(int(stdout[1]))

    # Conda configuration files are not present in the distribution, but only
    # in the GIT repository of the source code.
    meta = pathlib.Path(WORKING_DIRECTORY, 'conda', 'meta.yaml')
    if meta.exists():
        update_meta(meta, version)
        update_environment(
            pathlib.Path(WORKING_DIRECTORY, 'conda', 'environment.yml'),
            version)
        update_environment(
            pathlib.Path(WORKING_DIRECTORY, 'binder', 'environment.yml'),
            version)

    # Updating the version number description for sphinx
    conf = pathlib.Path(WORKING_DIRECTORY, 'docs', 'source', 'conf.py')
    with open(conf, "r") as stream:
        lines = stream.readlines()
    pattern = re.compile(r'(\w+)\s+=\s+(.*)')

    for idx, line in enumerate(lines):
        match = pattern.search(line)
        if match is not None:
            if match.group(1) == 'version':
                lines[idx] = "version = %r\n" % version
            elif match.group(1) == 'release':
                lines[idx] = "release = %r\n" % version
            elif match.group(1) == 'copyright':
                lines[idx] = "copyright = '(%s, CNES/CLS)'\n" % date.year

    with open(conf, "w") as stream:
        stream.write("".join(lines))

    # Finally, write the file containing the version number.
    with open(module, 'w') as handler:
        handler.write('''# Copyright (c) 2022 CNES
#
# All rights reserved. Use of this source code is governed by a
# BSD-style license that can be found in the LICENSE file.
"""
Get software version information
================================
"""


def release() -> str:
    """Returns the software version number"""
    return "{version}"


def date() -> str:
    """Returns the creation date of this release"""
    return "{date}"
'''.format(version=version, date=date.strftime("%d %B %Y")))
    return version


# pylint: disable=too-few-public-methods
class CMakeExtension(setuptools.Extension):
    """Python extension to build"""

    def __init__(self, name):
        super(CMakeExtension, self).__init__(name, sources=[])

    # pylint: enable=too-few-public-methods


class BuildExt(setuptools.command.build_ext.build_ext):
    """Build the Python extension using cmake"""

    #: Preferred BOOST root
    BOOST_ROOT: ClassVar[Optional[str]] = None

    #: Build the unit tests of the C++ extension
    BUILD_INITTESTS: ClassVar[Optional[bool]] = None

    #: Enable coverage reporting
    CODE_COVERAGE: ClassVar[Optional[bool]] = None

    #: Generation of the conda-forge package
    CONDA_FORGE: ClassVar[Optional[bool]] = None

    #: Preferred C compiler
    C_COMPILER: ClassVar[Optional[str]] = None

    #: Preferred C++ compiler
    CXX_COMPILER: ClassVar[Optional[str]] = None

    #: Preferred Eigen root
    EIGEN3_INCLUDE_DIR: ClassVar[Optional[str]] = None

    #: Selected CMAKE generator
    GENERATOR: ClassVar[Optional[str]] = None

    #: Preferred GSL root
    GSL_ROOT: ClassVar[Optional[str]] = None

    #: Preferred MKL root
    MKL_ROOT: ClassVar[Optional[str]] = None

    #: Run CMake to configure this project
    RECONFIGURE: ClassVar[Optional[bool]] = None

    #: Use of MKL
    MKL: ClassVar[Optional[bool]] = None

    def run(self):
        """A command's raison d'etre: carry out the action"""
        for ext in self.extensions:
            self.build_cmake(ext)
        super().run()

    @classmethod
    def gsl(cls):
        """Get the default boost path in Anaconda's environnement."""
        gsl_root = sys.prefix
        if pathlib.Path(gsl_root, "include", "gsl").exists():
            return "-DGSL_ROOT_DIR=" + gsl_root
        gsl_root = pathlib.Path(sys.prefix, "Library")
        if not gsl_root.joinpath("include", "gsl").exists():
            if cls.CONDA_FORGE:
                raise RuntimeError(
                    "Unable to find the GSL library in the conda distribution "
                    "used.")
            return None
        return "-DGSL_ROOT_DIR=" + str(gsl_root)

    @classmethod
    def boost(cls):
        """Get the default boost path in Anaconda's environnement."""
        # Do not search system for Boost & disable the search for boost-cmake
        boost_option = "-DBoost_NO_SYSTEM_PATHS=TRUE " \
            "-DBoost_NO_BOOST_CMAKE=TRUE"
        boost_root = sys.prefix
        if pathlib.Path(boost_root, "include", "boost").exists():
            return "{boost_option} -DBOOST_ROOT={boost_root}".format(
                boost_root=boost_root, boost_option=boost_option).split()
        boost_root = pathlib.Path(sys.prefix, "Library", "include")
        if not boost_root.exists():
            if cls.CONDA_FORGE:
                raise RuntimeError(
                    "Unable to find the Boost library in the conda "
                    "distribution used.")
            return None
        return "{boost_option} -DBoost_INCLUDE_DIR={boost_root}".format(
            boost_root=boost_root, boost_option=boost_option).split()

    @classmethod
    def eigen(cls):
        """Get the default Eigen3 path in Anaconda's environnement."""
        eigen_include_dir = pathlib.Path(sys.prefix, "include", "eigen3")
        if eigen_include_dir.exists():
            return "-DEIGEN3_INCLUDE_DIR=" + str(eigen_include_dir)
        eigen_include_dir = pathlib.Path(sys.prefix, "Library", "include",
                                         "eigen3")
        if not eigen_include_dir.exists():
            eigen_include_dir = eigen_include_dir.parent
        if not eigen_include_dir.exists():
            if cls.CONDA_FORGE:
                raise RuntimeError(
                    "Unable to find the Eigen3 library in the conda "
                    "distribution used.")
            return None
        return "-DEIGEN3_INCLUDE_DIR=" + str(eigen_include_dir)

    @staticmethod
    def mkl():
        """Get the default MKL path in Anaconda's environnement."""
        mkl_header = pathlib.Path(sys.prefix, "include", "mkl.h")
        if mkl_header.exists():
            os.environ["MKLROOT"] = sys.prefix
            return

        # Walkaround a problem of generation with Windows and CMake
        # (fixed in CMake 3.17)

        # mkl_header = pathlib.Path(sys.prefix, "Library", "include", "mkl.h")
        # if mkl_header.exists():
        #     os.environ["MKLROOT"] = str(pathlib.Path(sys.prefix, "Library"))
        #     return
        # raise RuntimeError(
        #     "Unable to find the MKL library in the conda distribution "
        #     "used.")

    @staticmethod
    def is_conda():
        """Detect if the Python interpreter is part of a conda distribution."""
        result = pathlib.Path(sys.prefix, 'conda-meta').exists()
        if not result:
            try:
                # pylint: disable=unused-import
                import conda  # noqa: F401

                # pylint: enable=unused-import
            except ImportError:
                result = False
            else:
                result = True
        return result

    def set_cmake_user_options(self):
        """Sets the options defined by the user."""
        is_conda = self.is_conda()
        result = []

        if self.C_COMPILER is not None:
            result.append("-DCMAKE_C_COMPILER=" + self.C_COMPILER)

        if self.CXX_COMPILER is not None:
            result.append("-DCMAKE_CXX_COMPILER=" + self.CXX_COMPILER)

        if self.CONDA_FORGE:
            result.append("-DCONDA_FORGE=ON")

        if self.BOOST_ROOT is not None:
            result.append("-DBOOSTROOT=" + self.BOOST_ROOT)
        elif is_conda:
            cmake_variable = self.boost()
            if cmake_variable:
                result += cmake_variable

        if self.GSL_ROOT is not None:
            result.append("-DGSL_ROOT_DIR=" + self.GSL_ROOT)
        elif is_conda:
            cmake_variable = self.gsl()
            if cmake_variable:
                result.append(cmake_variable)

        if self.EIGEN3_INCLUDE_DIR is not None:
            result.append("-DEIGEN3_INCLUDE_DIR=" + self.EIGEN3_INCLUDE_DIR)
        elif is_conda:
            cmake_variable = self.eigen()
            if cmake_variable:
                result.append(cmake_variable)

        if self.MKL_ROOT is not None:
            os.environ["MKLROOT"] = self.MKL_ROOT
        elif is_conda and self.MKL:
            self.mkl()

        return result

    def build_cmake(self, ext):
        """Execute cmake to build the Python extension"""
        # These dirs will be created in build_py, so if you don't have
        # any python sources to bundle, the dirs will be missing
        build_temp = pathlib.Path(WORKING_DIRECTORY, self.build_temp)
        build_temp.mkdir(parents=True, exist_ok=True)
        extdir = str(build_dirname(ext.name))

        cfg = 'Debug' if self.debug or self.CODE_COVERAGE else 'Release'

        cmake_args = [
            "-DCMAKE_BUILD_TYPE=" + cfg, "-DCMAKE_LIBRARY_OUTPUT_DIRECTORY=" +
            str(extdir), "-DPYTHON_EXECUTABLE=" + sys.executable
        ] + self.set_cmake_user_options()

        build_args = ['--config', cfg]

        is_windows = platform.system() == "Windows"

        if self.GENERATOR is not None:
            cmake_args.append("-G" + self.GENERATOR)
        elif is_windows:
            cmake_args.append("-G" + 'Visual Studio 16 2019')

        if not is_windows:
            build_args += ['--', '-j%d' % os.cpu_count()]
            if platform.system() == 'Darwin':
                cmake_args += [
                    '-DCMAKE_OSX_DEPLOYMENT_TARGET=' + OSX_DEPLOYMENT_TARGET
                ]
            if self.CODE_COVERAGE:
                cmake_args += ["-DCODE_COVERAGE=ON"]
        else:
            cmake_args += [
                '-DCMAKE_GENERATOR_PLATFORM=x64',
                '-DCMAKE_LIBRARY_OUTPUT_DIRECTORY_{}={}'.format(
                    cfg.upper(), extdir)
            ]
            build_args += ['--', '/m']
            if self.verbose:  # type: ignore
                build_args += ['/verbosity:n']

        if self.verbose:  # type: ignore
            build_args.insert(0, "--verbose")

        os.chdir(str(build_temp))

        # Has CMake ever been executed?
        if pathlib.Path(build_temp, "CMakeFiles",
                        "TargetDirectories.txt").exists():
            # The user must force the reconfiguration
            configure = self.RECONFIGURE is not None
        else:
            configure = True

        if configure:
            self.spawn(['cmake', str(WORKING_DIRECTORY)] + cmake_args)
        if not self.dry_run:  # type: ignore
            cmake_cmd = ['cmake', '--build', '.']
            if self.BUILD_INITTESTS is None:
                cmake_cmd += ['--target', 'core']
            self.spawn(cmake_cmd + build_args)
        os.chdir(str(WORKING_DIRECTORY))


class Build(distutils.command.build.build):
    """Build everything needed to install"""
    user_options = distutils.command.build.build.user_options
    user_options += [
        ('boost-root=', None, 'Preferred Boost installation prefix'),
        ('build-unittests', None, "Build the unit tests of the C++ extension"),
        ('conda-forge', None, "Generation of the conda-forge package"),
        ('code-coverage', None, 'Enable coverage reporting'),
        ('c-compiler=', None, 'Preferred C compiler'),
        ('cxx-compiler=', None, 'Preferred C++ compiler'),
        ('eigen-root=', None, 'Preferred Eigen3 include directory'),
        ('generator=', None, 'Selected CMake generator'),
        ('gsl-root=', None, 'Preferred GSL installation prefix'),
        ('mkl-root=', None, 'Preferred MKL installation prefix'),
        ('mkl=', None, 'Using MKL as BLAS library'),
        ('reconfigure', None, 'Forces CMake to reconfigure this project')
    ]

    boolean_options = distutils.command.build.build.boolean_options
    boolean_options += ["mkl"]
    boolean_options += ["conda-forge"]

    def initialize_options(self):
        """Set default values for all the options that this command supports"""
        super().initialize_options()
        self.boost_root = None
        self.build_unittests = None
        self.conda_forge = None
        self.code_coverage = None
        self.c_compiler = None
        self.cxx_compiler = None
        self.eigen_root = None
        self.generator = None
        self.gsl_root = None
        self.mkl = None
        self.mkl_root = None
        self.reconfigure = None

    def finalize_options(self):
        """Set final values for all the options that this command supports"""
        super().finalize_options()
        if self.code_coverage is not None and platform.system() == 'Windows':
            raise RuntimeError("Code coverage is not supported on Windows")
        if self.mkl_root is not None:
            self.mkl = True
        if not self.mkl and self.mkl_root:
            raise RuntimeError(
                "argument --mkl_root not allowed with argument --mkl=no")

    def run(self):
        """A command's raison d'etre: carry out the action"""
        if self.boost_root is not None:
            BuildExt.BOOST_ROOT = self.boost_root
        if self.build_unittests is not None:
            BuildExt.BUILD_INITTESTS = self.build_unittests
        if self.code_coverage is not None:
            if platform.system() == 'Windows':
                raise RuntimeError("Code coverage is not supported on Windows")
            BuildExt.CODE_COVERAGE = self.code_coverage
        if self.conda_forge is not None:
            BuildExt.CONDA_FORGE = bool(self.conda_forge)
        if self.c_compiler is not None:
            BuildExt.C_COMPILER = self.c_compiler
        if self.cxx_compiler is not None:
            BuildExt.CXX_COMPILER = self.cxx_compiler
        if self.eigen_root is not None:
            BuildExt.EIGEN3_INCLUDE_DIR = self.eigen_root
        if self.generator is not None:
            BuildExt.GENERATOR = self.generator
        if self.gsl_root is not None:
            BuildExt.GSL_ROOT = self.gsl_root
        if self.mkl_root is not None:
            BuildExt.MKL_ROOT = self.mkl_root
        if self.reconfigure is not None:
            BuildExt.RECONFIGURE = True
        if self.mkl is not None:
            BuildExt.MKL = bool(self.mkl)
        super().run()


class Test(setuptools.Command):
    """Test runner"""
    description = "run pytest"
    user_options = [('ext-coverage', None,
                     "Generate C++ extension coverage reports"),
                    ("pytest-args=", None, "Arguments to pass to pytest")]

    def initialize_options(self):
        """Set default values for all the options that this command
        supports"""
        self.ext_coverage = None
        self.pytest_args = None

    def finalize_options(self):
        """Set final values for all the options that this command supports"""
        if self.pytest_args is None:
            self.pytest_args = ''
        self.pytest_args = " --pyargs pyinterp " + self.pytest_args

    @staticmethod
    def tempdir():
        """Gets the build directory of the extension"""
        return pathlib.Path(
            WORKING_DIRECTORY, "build",
            "temp.%s-%d.%d" % (sysconfig.get_platform(), MAJOR, MINOR))

    def run(self):
        """Run tests"""
        import pytest
        sys.path.insert(0, str(build_dirname()))

        errno = pytest.main(
            shlex.split(
                self.pytest_args,  # type: ignore
                posix=platform.system() != 'Windows'))
        if errno:
            sys.exit(errno)

        # Directory used during the generating the C++ extension.
        tempdir = self.tempdir()

        # We work in the extension generation directory (CMake directory)
        os.chdir(str(tempdir))

        # If the C++ unit tests have been generated, they are executed.
        if pathlib.Path(tempdir, "src", "pyinterp", "core", "tests",
                        "test_axis").exists():
            self.spawn(["ctest", "--output-on-failure"])

        # Generation of the code coverage of the C++ extension?
        if not self.ext_coverage:
            return

        # Directory for writing the HTML coverage report.
        htmllcov = str(pathlib.Path(tempdir.parent.parent, "htmllcov"))

        # File containing the coverage report.
        coverage_info = str(pathlib.Path(tempdir, "coverage.info"))

        # Collect coverage data from python/C++ unit tests
        self.spawn([
            "lcov", "--capture", "--directory",
            str(tempdir), "--output-file", coverage_info
        ])

        # The coverage of third-party libraries is removed.
        self.spawn([
            'lcov', '-r', coverage_info, "*/Xcode.app/*", "*/third_party/*",
            "*/boost/*", "*/eigen3/*", "*/tests/*", "*/usr/*", '--output-file',
            coverage_info
        ])

        # Finally, we generate the HTML coverage report.
        self.spawn(["genhtml", coverage_info, "--output-directory", htmllcov])


class SDist(setuptools.command.sdist.sdist):
    """Custom sdist command that copies the pytest configuration file
    into the package"""
    user_options = setuptools.command.sdist.sdist.user_options

    def run(self):
        """A command's raison d'etre: carry out the action"""
        source = WORKING_DIRECTORY.joinpath("conftest.py")
        target = WORKING_DIRECTORY.joinpath("src", "pyinterp", "conftest.py")
        source.rename(target)
        try:
            super().run()
        finally:
            target.rename(source)


def long_description():
    """Reads the README file"""
    with open(pathlib.Path(WORKING_DIRECTORY, "README.rst")) as stream:
        return stream.read()


def typehints():
    """Get the list of type information files"""
    pyi = []
    for root, _, files in os.walk(WORKING_DIRECTORY):
        pyi += [
            str(pathlib.Path(root, item).relative_to(WORKING_DIRECTORY))
            for item in files if item.endswith('.pyi')
        ]
    return [(str(pathlib.Path('pyinterp', 'core')), pyi)]


def main():
    """Main function"""
    install_requires = [
        "dask", "fsspec", "numpy", "numcodecs", "toolz", "xarray >= 0.13"
    ]
    tests_require = install_requires + ["NetCDF4", "pytest"]
    setuptools.setup(
        author='CNES/CLS',
        author_email='fbriol@gmail.com',
        classifiers=[
            "Development Status :: 4 - Beta",
            "Topic :: Scientific/Engineering :: Physics",
            "License :: OSI Approved :: BSD License",
            "Natural Language :: English", "Operating System :: POSIX",
            "Operating System :: MacOS",
            "Operating System :: Microsoft :: Windows",
            "Programming Language :: Python :: 3.6",
            "Programming Language :: Python :: 3.7",
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: 3.9",
            "Programming Language :: Python :: 3.10"
        ],
        cmdclass={
            'build': Build,
            'build_ext': BuildExt,
            'sdist': SDist,
            'test': Test
        },  # type: ignore
        data_files=typehints(),
        description='Interpolation of geo-referenced data for Python.',
        ext_modules=[CMakeExtension(name="pyinterp.core")],
        install_requires=install_requires,
        license="BSD License",
        long_description=long_description(),
        long_description_content_type='text/x-rst',
        name='pyinterp',
        package_data={
            'pyinterp': ['py.typed'],
            'pyinterp.tests': ["dataset/*"],
        },
        package_dir={'': 'src'},
        packages=setuptools.find_namespace_packages(
            where='src',
            exclude=['pyinterp.core*'],
        ),
        platforms=['POSIX', 'MacOS', 'Windows'],
        python_requires='>=3.6',
        tests_require=tests_require,
        url='https://github.com/CNES/pangeo-pyinterp',
        version=revision(),
        zip_safe=False,
    )


if __name__ == "__main__":
    if platform.system() == 'Darwin':
        os.environ['MACOSX_DEPLOYMENT_TARGET'] = OSX_DEPLOYMENT_TARGET
    main()
