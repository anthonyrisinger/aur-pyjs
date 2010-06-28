# -*- coding: utf-8 -*-
from pyjamas import DOM, History
from pyjamas.ui.RootPanel import RootPanel
from pyjamas.ui.Label import Label
from pyjamas.ui.HTML import HTML
from pyjamas.ui.VerticalPanel import VerticalPanel
from pyjamas.ui.HorizontalPanel import HorizontalPanel
from pyjamas.ui.SimplePanel import SimplePanel
from pyjamas.ui.Image import Image
from pyjamas.ui.Hyperlink import Hyperlink
from pyjamas.ui.TextBox import TextBox
from pyjamas.ui.ListBox import ListBox
from pyjamas.ui.Button import Button
from Views.content import home, searchResults, underConstruction
from __pyjamas__ import console

import Search

# global handle for the Main instance
APP = None

#COPYRIGHT=[
#    {'name':'Judd Vinet', 'link':'mailto:jvinet@zeroflux.org'},
#    {'name':'Aaron Griffin', 'link':'mailto:aaron@archlinux.org'}
#]
COPYRIGHT=[
    {'name':'XXXXXX', 'link':'#'},
    {'name':'XXXXXX', 'link':'#'}
]

class Main:

    def __init__(self, parent=None):
        self.parent = RootPanel(parent)
        self.screen = VerticalPanel(ID='aur-screen', Width='100%', Height='100%')
        self.content = SimplePanel(ID='aur-content', Width='100%')
        self.contentProvider = {}
        self.contentCache = {}
        self.contentActive = None
        self.onLoad()

    def setContentActive(self, target, cache_target=True, cache_use=True):
        provider = self.contentProvider.get(target)
        if provider is None: provider = self.contentProvider.get(None)
        if provider is None: return False
        cache = None
        if cache_use: cache = self.contentCache.get(target)
        widget = provider(getattr(self, 'content'), cache)
        res = (widget == self.content.getWidget())
        if cache_target and res and self.contentCache.get(target) != widget:
            self.contentCache[target] = widget
        if res: self.contentActive = target
        return res

    def setContentProvider(self, target, provider):
        self.contentProvider[target] = provider
    
    def onHistoryChanged(self):
        self.setContentActive(History.getToken())

    def onLoad(self):
        History.addHistoryListener(self)
        self.setContentProvider(None, home.provider)
        self.setContentProvider('/home', home.provider)
        self.setContentProvider('/account', underConstruction.provider)
        self.setContentProvider('/package', underConstruction.provider)
        self.setContentProvider('/package/search', searchResults.provider)
        self.setContentProvider('/user', underConstruction.provider)
        self.setContentProvider('/submit', underConstruction.provider)
        self.draw()

    def draw(self):
        parent = self.parent
        screen = self.screen
        content = self.content
        header = HorizontalPanel(ID='aur-header', Width='100%')
        boundary = SimplePanel(ID='aur-boundary', StyleName='aur-link-stateful')
        container = VerticalPanel(ID='aur-container', Width='100%', Height='100%')

        parent.add(screen)

        screen.add(header)
        screen.setCellHeight(header, "1px")
        screen.add(boundary)
        boundary.add(container)

        self.drawHeader(header)
        self.drawBody(container)

        self.onHistoryChanged()

    def drawHeader(self, container):
        logo = Image(ID='aur-logo', url='http://www.archlinux.org/media/archnavbar/archlogo.gif', Width='190px', Height='40px')
        menu = HorizontalPanel(ID='aur-menu-ext')
        container.add(logo)
        container.add(menu)
        container.setCellWidth(menu, "1px")
        self.drawExternalMenu(menu)

    def drawBody(self, container):
        menu = HorizontalPanel(ID='aur-menu-int')
        search_cont = SimplePanel(StyleName='aur-content-boundary')
        search = VerticalPanel(ID='aur-search')
        footer = VerticalPanel(ID='aur-footer', Width='100%', HorizontalAlignment='center')
        search_cont.add(search)
        container.add(menu)
        container.add(search_cont)
        container.add(self.content)
        container.add(footer)
        container.setCellHeight(menu, "1px")
        container.setCellHeight(footer, "1px")
        container.setCellHorizontalAlignment(footer, 'center')
        self.drawInternalMenu(menu)
        Search.draw(search)
        self.drawFooter(footer)

    def drawExternalMenu(self, container):
        # we have to use HTML() widgets here for external links, no Anchor widget in pyjamas (yet) :-(
        container.add(HTML('<a href="http://www.archlinux.org/">Home</a>', StyleName='aur-menu-ext-item', Title='Arch news, projects, packages and more'))
        container.add(HTML('<a href="http://www.archlinux.org/packages/">Packages</a>', StyleName='aur-menu-ext-item', Title='Arch Package Database'))
        container.add(HTML('<a href="http://bbs.archlinux.org/">Forums</a>', StyleName='aur-menu-ext-item', Title='Community forums'))
        container.add(HTML('<a href="http://wiki.archlinux.org/">Wiki</a>', StyleName='aur-menu-ext-item', Title='Community documentation'))
        container.add(HTML('<a href="http://bugs.archlinux.org/">Bugs</a>', StyleName='aur-menu-ext-item', Title='Report and track bugs'))
        container.add(Hyperlink(Text='AUR', TargetHistoryToken='', StyleName='aur-menu-ext-item aur-menu-ext-item-selected', Title='Arch Linux User Repository'))
        container.add(HTML('<a href="http://www.archlinux.org/download">Download</a>', StyleName='aur-menu-ext-item', Title='Get Arch Linux'))

    def drawInternalMenu(self, container):
        container.add(Hyperlink(Text='AUR Home', TargetHistoryToken='/home', StyleName='aur-link-stateless', Title='Return to AUR home'))
        container.add(Hyperlink(Text='Accounts', TargetHistoryToken='/account', StyleName='aur-link-stateless', Title='Create/Edit user account'))
        container.add(Hyperlink(Text='Packages', TargetHistoryToken='/package', StyleName='aur-link-stateless', Title='Browse packages'))
        container.add(HTML('<a href="http://bugs.archlinux.org/index.php?tasks=all&project=2">Bugs</a>', StyleName='aur-link-stateless', Title='AUR bugtracker'))
        container.add(HTML('<a href="http://archlinux.org/mailman/listinfo/aur-general">Discussion</a>', StyleName='aur-link-stateless', Title='AUR mailing list'))
        container.add(Hyperlink(Text='My Packages', TargetHistoryToken='/users', StyleName='aur-link-stateless', Title='View maintained packages', Visible=False))
        container.add(Hyperlink(Text='Submit', TargetHistoryToken='/submit', StyleName='aur-link-stateless', Title='Submit/Update package to AUR', Visible=False))

    def drawFooter(self, container):
        # dictionary coercion not supported
        tpl = '<a href="%s" title="Contact %s">%s</a>'
        copyright = ' and '.join([tpl % (holder['link'], holder['name'], holder['name']) for holder in COPYRIGHT])
        container.add(HTML('Copyright &copy; 2002-2010 ' + copyright + '.'))
        container.add(HTML('The Arch Linux name and logo are recognized <a href="http://wiki.archlinux.org/index.php/DeveloperWiki:TrademarkPolicy" title="Arch Linux Trademark Policy">trademarks</a>. Some rights reserved.'))
        container.add(HTML('The registered trademark Linux® is used pursuant to a sublicense from LMI, the exclusive licensee of Linus Torvalds, owner of the mark on a world-wide basis.'))

if __name__ == '__main__':
    APP = Main()
