# -*- coding: utf-8 -*-
from pyjamas.ui import VerticalPanel, Label
from pyjamas.ui.SimplePanel import SimplePanel

import Search

def provider(content, cache=None):
    cont = SimplePanel(StyleName='aur-content-boundary')
    home = VerticalPanel.VerticalPanel(Width='100%', Height='100%', HorizontalAlignment='center', VerticalAlignment='middle')
    content.setWidget(cont)
    cont.setWidget(home)
    doBuildContent(home)
    return cont

def doBuildContent(container):
    container.add(Label.Label(Search.walkStack(Search.TOGGLE_STACK)))
