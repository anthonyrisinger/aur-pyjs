# -*- coding: utf-8 -*-
from pyjamas.ui.RootPanel import RootPanel
from pyjamas.ui.HTML import HTML
from pyjamas.ui.VerticalPanel import VerticalPanel
from pyjamas.ui.HorizontalPanel import HorizontalPanel
from pyjamas.ui.SimplePanel import SimplePanel
from pyjamas.ui.Image import Image
from pyjamas.ui.Hyperlink import Hyperlink

from lib.gui.core import App


class StageComponent(object):

    LOGO = {
        'url': 'http://www.archlinux.org/media/archnavbar/archlogo.gif',
        'Width': '190px',
        'Height': '40px',
    }

    MENU_EXTERNAL = [
        ('Home', 'Arch news, projects, packages and more', 'http://www.archlinux.org/'),
        ('Packages', 'Arch Package Database', 'http://www.archlinux.org/packages/'),
        ('Forums', 'Community forums', 'http://bbs.archlinux.org/'),
        ('Wiki', 'Community documentation', 'http://wiki.archlinux.org/'),
        ('Bugs', 'Report and track bugs', 'http://bugs.archlinux.org/'),
        ('AUR', 'Arch Linux User Repository', '/'),
        ('Download', 'Get Arch Linux', 'http://www.archlinux.org/download/'),
    ]

    MENU_INTERNAL = [
        ('AUR home', 'Return to AUR home', '/'),
        ('Accounts', 'Create/Edit user account', '/accounts'),
        ('Packages', 'Browse packages', '/packages'),
        ('Bugs', 'AUR bugtracker', 'http://bugs.archlinux.org/index.php?tasks=all&project=2'),
        ('Submit', 'Submit/Update package to AUR', '/upload'),
    ]

    def __init__(self, parent=None):
        self.parent = RootPanel(parent)
        self.screen = VerticalPanel(ID='aur-screen', Width='100%', Height='100%')
        self.content = SimplePanel(ID='aur-content', Width='100%')
        self.header = HorizontalPanel(ID='aur-header', Width='100%')
        self.boundary = SimplePanel(ID='aur-boundary', StyleName='aur-link-stateful')
        self.container = VerticalPanel(ID='aur-container', Width='100%', Height='100%')
        self.logo = Image(ID='aur-logo', **self.LOGO)
        self.menu_external = HorizontalPanel(ID='aur-menu-ext')
        self.menu_internal = HorizontalPanel(ID='aur-menu-int')
        self.search_cont = SimplePanel(StyleName='aur-content-boundary')
        self.search = VerticalPanel(ID='aur-search')
        self.footer = VerticalPanel(ID='aur-footer', Width='100%', HorizontalAlignment='center')

    def draw(self):
        self.parent.add(self.screen)
        self.screen.add(self.header)
        self.screen.setCellHeight(self.header, "1px")
        self.screen.add(self.boundary)
        self.boundary.add(self.container)
        self.draw_head(self.header)
        self.draw_body(self.container)
        self.draw_foot(self.container)

    def draw_head(self, container):
        container.add(self.logo)
        container.add(self.menu_external)
        container.setCellWidth(self.menu_external, "1px")
        self.draw_menu_external(self.menu_external)

    def draw_body(self, container):
        container.add(self.menu_internal)
        container.add(self.search_cont)
        self.search_cont.add(self.search)
        container.add(self.content)
        container.setCellHeight(self.menu_internal, "1px")
        self.draw_menu_internal(self.menu_internal)
        #Search.draw(search)

    def draw_menu_external(self, container):
        for name, title, uri in self.MENU_EXTERNAL:
            if uri.startswith('http'):
                html = '<a href="%s" title="%s">%s</a>' % (uri, title, name)
                link = HTML(HTML=html, StyleName='aur-menu-ext-item')
            else:
                link = Hyperlink(Text=name, Title=title, TargetHistoryToken=uri,
                           StyleName='aur-menu-ext-item aur-menu-ext-item-selected')
            container.add(link)

    def draw_menu_internal(self, container):
        for name, title, uri in self.MENU_INTERNAL:
            if uri.startswith('http'):
                html = '<a href="%s" title="%s">%s</a>' % (uri, title, name)
                link = HTML(HTML=html, StyleName='aur-menu-int-item')
            else:
                link = Hyperlink(Text=name, Title=title, TargetHistoryToken=uri,
                           StyleName='aur-menu-int-item')
            container.add(link)

    def draw_foot(self, container):
        def mklink(name, title, uri):
            return '<a href="%s" title="%s">%s</a>' % (uri, title, name)
        trademark = ( 
            'trademarks',
            'Arch Linux Trademark Policy',
            'http://wiki.archlinux.org/index.php/DeveloperWiki:TrademarkPolicy',
        )
        sections = []
        sections.append(
            'Copyright &copy; 2002-2010 ' +
            ' and '.join([mklink(*holder) for holder in App.COPYRIGHT]) +
            '.'
        )
        sections.append(
            'The Arch Linux name and logo are recognized ' +
            mklink(*trademark) +
            '. Some rights reserved.'
        )
        sections.append(
            'The registered trademark Linux&reg; is used pursuant to a sublicense from LMI, ' +
            'the exclusive licensee of Linus Torvalds, owner of the mark on a world-wide basis.'
        )
        foot = HTML('<br/>'.join(sections), ID='aur-footer')
        container.add(foot)
        container.setCellHeight(foot, "1px")
        container.setCellHorizontalAlignment(foot, 'center')
