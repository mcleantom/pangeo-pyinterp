# Copyright (c) 2024 CNES
#
# All rights reserved. Use of this source code is governed by a
# BSD-style license that can be found in the LICENSE file.
"""
Get software version information
================================
"""

from .__version__ import version


def release() -> str:
    """Returns the software version number"""
    return version()


def date() -> str:
    """Returns the creation date of this release"""
    return "13 February 2024"
