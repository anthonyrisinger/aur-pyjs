#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
# This file not meant to be ran directly; it's
# the top-level file used for translation.
#
try:
    import sys
    sys.setappname('aur')
except AttributeError:
    raise RuntimeError('This file is not for use by python; use desktop.py')

from lib.gui import core


if __name__ == '__main__':
    core.main()
