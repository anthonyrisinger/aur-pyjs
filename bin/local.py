#!/usr/bin/env python2
# -*- coding: utf-8 -*-
import sys
from os import path
import lib.ext

base = path.dirname(path.dirname(path.realpath(__file__)))
sys.path[0:0] = [base]

import pyjd
from lib.gui import core

if __name__ == '__main__':
   if len(sys.argv) != 2:
       fname = path.join(base, 'pub', 'aur.html')
   else:
       fname = sys.argv[1]
   pyjd.setup(fname)
   core.main()
   pyjd.run()
