# -*- coding: utf-8 -*-
from pyjamas.ui.Label import Label

def provider(content, cache=None):
    if cache is not None:
        content.setWidget(cache)
        return cache
    widget = Label('Coming Soon!')
    content.setWidget(widget)
    return widget
