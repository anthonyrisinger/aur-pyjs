# -*- coding: utf-8 -*-
from pyjamas import History
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
from pyjamas.ui.Calendar import DateField
from pyjamas.ui.CheckBox import CheckBox

DateField.icon_img = 'ico/calendar_view_month.png'

class Object(object):
    pass

# module variables
TOGGLE = [
    {
        'index': 0,
        'item': 'Arch',
        'value': 'arch',
        'allowsOperator': (),
        'allowsInverse': False,
        'allowsMultiple': False,
        'widget': ListBox,
        'params': [
            ('Any', '_'),
            ('i686', '32'),
            ('x86_64', '64')
        ]
    },
    {
        'index': 1,
        'item': 'Category',
        'value': 'cat',
        'allowsOperator': ('and', 'or'),
        'allowsInverse': True,
        'allowsMultiple': True,
        'widget': ListBox,
        'params': [
            ('Any', '_'),
            ('daemons', 1),
            ('devel', 2),
            ('editors', 3),
            ('emulators', 4),
            ('games', 5),
            ('gnome', 6),
            ('i18n', 7),
            ('kde', 8),
            ('kernels', 9),
            ('lib', 10),
            ('modules', 11),
            ('multimedia', 12),
            ('network', 13),
            ('office', 14),
            ('science', 15),
            ('system', 16),
            ('x11', 17),
            ('xfce', 18)
        ]
    },
    {
        'index': 2,
        'item': 'Updated since',
        'value': 'last_update',
        'allowsOperator': (),
        'allowsInverse': True,
        'allowsMultiple': False,
        'widget': DateField,
        'params': []
    },
    {
        'index': 3,
        'item': 'Out of date',
        'value': 'is_old',
        'allowsOperator': (),
        'allowsInverse': False,
        'allowsMultiple': False,
        'widget': CheckBox,
        'params': [ False ]
    },
    {
        'index': 4,
        'item': 'Orphans only',
        'value': 'is_orphan',
        'allowsOperator': (),
        'allowsInverse': False,
        'allowsMultiple': False,
        'widget': CheckBox,
        'params': [ False ]
    }
]

# FIXME: these need their own values
FILTER = TOGGLE
SORT = TOGGLE

# used later; walked to compile the search operation sent to server
TOGGLE_STACK = None
FILTER_STACK = None
SORT_STACK = None

def walkStack(node):
    chunks = []
    op = ' && ' if node.operator == 'and' else ' || '
    for param in node.parameters:
        invert = '!=' if param.isInverted else '='
        # FIXME: need to implement a getValue() method on the Param class
        expression = param.kind['value'] + invert + 'FIXME'
        chunks.append(expression)
    for child in node.children:
        invert = '!' if child.isInverted else ''
        chunks.append(invert + '(' + walkStack(child) + ')')
    return op.join(chunks)

def draw(container):
    header = Label('Arch User Repository', StyleName='aur-search-header')
    container.add(header)
    drawControl(container)

def drawControl(container):
    bar = HorizontalPanel(ID='aur-search-bar', VerticalAlignment='middle')
    adv = HorizontalPanel(ID='aur-search-advanced', Visible=False)
    adv_toggle = Hyperlink(Text='Advanced', StyleName='aur-link-stateless aur-search-bar-advanced', TargetHistoryToken=History.getToken())
    query = TextBox(Text='enter search term...', StyleName='aur-search-bar-query')
    go = Button(HTML='Go', StyleName='aur-search-bar-submit')

    container.add(bar)
    container.add(adv)

    # slight workaround to make sure the 'Advanced' toggle doesn't change the page
    def updateAdvToken(token):
        adv_toggle.setTargetHistoryToken(token)
    obj = Object()
    setattr(obj, 'onHistoryChanged', updateAdvToken)
    History.addHistoryListener(obj)

    # clickListener to toggle the advanced section
    def toggleAdv(sender):
        if adv.isVisible():
            adv.setVisible(False)
            query.setEnabled(True)
            adv_toggle.setText('Advanced')
        else:
            adv.setVisible(True)
            query.setEnabled(False)
            adv_toggle.setText('Basic')
    adv_toggle.addClickListener(toggleAdv)

    def doGo(sender):
        History.newItem('/package/search')
    go.addClickListener(doGo)

    bar.add(Label('Search Criteria', StyleName='aur-search-bar-label'))
    bar.add(query)
    bar.add(go)
    bar.add(Button(HTML='Orphans', StyleName='aur-search-bar-submit'))
    bar.add(adv_toggle)

    drawAdvanced(adv)

def drawAdvanced(container):
    global TOGGLE_STACK, FILTER_STACK, SORT_STACK
    TOGGLE_STACK = ParamGroup(container, TOGGLE, title='Toggle')
    FILTER_STACK = ParamGroup(container, FILTER, title='Filter')
    SORT_STACK = ParamGroup(container, SORT, title='Sort')
    # fix for spacing
    FILTER_STACK.panel.addStyleName('aur-search-advanced-group-middle')
    for x in range(container.getWidgetCount()):
        container.setCellWidth(container.getWidget(x), '1%')
    TOGGLE_STACK.addParamFull(None)
    FILTER_STACK.addParamFull(None)
    SORT_STACK.addParamFull(None)

class Param(object):
    def __init__(self, container, kind, group, draw=True):
        self.container = container
        self.kind = kind
        self.group = group
        self.panel = SimplePanel(StyleName='aur-search-advanced-param')
        self.isInverted = False
        # assigned by parent, visual use only
        self.op = None
        if draw: self.draw()

    def draw(self):
        paramPanel = HorizontalPanel(Width='100%', VerticalAlignment='middle')
        options = self.drawOptions()
        label = Label(self.kind['item'], StyleName='aur-search-advanced-param-title')
        delSelf = Image(url='ico/cross.png', Title='Delete this parameter')
        delSelf.addStyleName('aur-search-advanced-delete')
        if self.kind['allowsInverse']:
            invertSelf = Image(url='ico/exclamation.png', Title='Invert this parameter')
            invertSelf.addClickListener(getattr(self, 'invertSelf'))
        else:
            invertSelf = Image(url='ico/bullet_white.png', StyleName='aur-search-advanced-placeholder')
        self.container.add(self.panel)
        self.panel.setWidget(paramPanel)
        paramPanel.add(delSelf)
        paramPanel.add(label)
        paramPanel.add(options)
        paramPanel.add(invertSelf)
        paramPanel.setCellWidth(delSelf, '1px')
        paramPanel.setCellWidth(options, '1px')
        paramPanel.setCellWidth(invertSelf, '1px')
        delSelf.addClickListener(getattr(self, 'delSelf'))

    def drawOptions(self):
        widget = self.kind['widget']()
        if isinstance(widget, ListBox):
            for x in self.kind['params']:
                widget.addItem(str(x[0]), str(x[1]))
        elif isinstance(widget, TextBox):
            pass
        elif isinstance(widget, CheckBox):
            if self.kind['params'][0]:
                widget.setChecked(True)
        elif isinstance(widget, DateField):
            pass
        return widget

    def delSelf(self, sender):
        self.group.delParam(self)

    def invertSelf(self, sender):
        if self.isInverted:
            self.isInverted = False
            self.panel.removeStyleName('aur-search-advanced-param-inverted')
            self.op.setText(self.group.operator)
        else:
            self.isInverted = True
            self.panel.addStyleName('aur-search-advanced-param-inverted')
            self.op.setText(self.group.operator + ' not')

class ParamGroup(object):
    def __init__(self, container, kind, parent=None, level=0, draw=True, title=None):
        self.container = container
        self.kind = kind
        self.parent = parent
        self.level = level
        self.title = title
        self.panel = SimplePanel(StyleName='aur-search-advanced-group')
        if level % 2 == 0: self.panel.addStyleName('aur-search-advanced-group-nested')
        self.childPanel = VerticalPanel(StyleName='aur-search-advanced-group-list', Width='100%')
        self.paramPanel = VerticalPanel(StyleName='aur-search-advanced-param-list', Width='100%')
        self.listPanel = VerticalPanel(StyleName='aur-search-advanced-list-boundary', Width='100%', Visible=False)
        self.paramChooser = ListBox()
        self.children = []
        self.parameters = []
        self.isInverted = False
        self.operator = 'and'
        # assigned by parent, visual use only
        self.op = None if parent else Label('and')
        if draw: self.draw()

    def draw(self):
        cont = VerticalPanel(Width='100%')
        header = HorizontalPanel(Width='100%', VerticalAlignment='middle', StyleName='aur-search-advanced-group-header')
        params = self.paramChooser
        addParam = Image(url='ico/tick.png', Title='Add parameter to this group')
        addGroup = Image(url='ico/table_add.png', Title='Nest group within this group')
        addGroupFull = Image(url='ico/table_lightning.png', Title='Nest group within this group; all parameters')
        invertSelf = Image(url='ico/exclamation.png', Title='Invert this parameter group')
        self.container.add(self.panel)
        self.panel.setWidget(cont)
        cont.add(header)
        if self.parent:
            d = Image(url='ico/cross.png', Title='Delete this parameter group')
            d.addStyleName('aur-search-advanced-delete')
            header.add(d)
            header.setCellWidth(d, '1px')
            d.addClickListener(getattr(self, 'delSelf'))
        if self.title:
            t = Label(self.title, StyleName='aur-search-advanced-group-header-title')
            header.add(t)
            header.setCellWidth(t, '1px')
        header.add(params)
        header.add(addParam)
        header.add(addGroup)
        header.add(addGroupFull)
        header.add(invertSelf)
        header.setCellWidth(params, '1px')
        header.setCellWidth(addGroup, '1px')
        header.setCellWidth(addGroupFull, '1px')
        header.setCellWidth(invertSelf, '1px')
        for x in self.kind:
            params.addItem(str(x['item']), str(x['index']))
        cont.add(self.listPanel)
        self.listPanel.add(self.paramPanel)
        self.listPanel.add(self.childPanel)
        addParam.addClickListener(getattr(self, 'addParam'))
        addGroup.addClickListener(getattr(self, 'addGroup'))
        addGroupFull.addClickListener(getattr(self, 'addGroupFull'))
        invertSelf.addClickListener(getattr(self, 'invertSelf'))

    def addGroup(self, sender):
        self.listPanel.setVisible(True)
        op = Label(self.operator, Title='Invert group operator', StyleName='aur-search-advanced-group-op', Visible=False)
        op.addClickListener(getattr(self, 'invertOperator'))
        if len(self.children) > 0 or len(self.parameters) > 0: op.setVisible(True)
        self.childPanel.add(op)
        self.childPanel.setCellHorizontalAlignment(op, 'right')
        g = ParamGroup(self.childPanel, self.kind, self, self.level+1)
        g.op = op
        self.children.append(g)

    def addGroupFull(self, sender):
        # this is a little hacky, but it's so fast you don't see it
        self.addGroup(None)
        group = self.children[len(self.children)-1]
        for x in range(group.paramChooser.getItemCount()):
            group.paramChooser.setSelectedIndex(x)
            group.addParam(None)
        group.paramChooser.setSelectedIndex(0)

    def addParam(self, sender):
        self.listPanel.setVisible(True)
        op = Label(self.operator, Title='Invert group operator', StyleName='aur-search-advanced-param-op', Visible=False)
        op.addClickListener(getattr(self, 'invertOperator'))
        if len(self.parameters) > 0: op.setVisible(True)
        self.paramPanel.add(op)
        self.paramPanel.setCellHorizontalAlignment(op, 'right')
        k = self.kind[int(self.paramChooser.getSelectedValues()[0])]
        p = Param(self.paramPanel, k, self)
        p.op = op
        self.parameters.append(p)
        if len(self.children) > 0:
            self.children[0].op.setVisible(True)

    def addParamFull(self, sender):
        # this is a little hacky, but it's so fast you don't see it
        old = self.paramChooser.getSelectedIndex()
        for x in range(self.paramChooser.getItemCount()):
            self.paramChooser.setSelectedIndex(x)
            self.addParam(None)
        self.paramChooser.setSelectedIndex(old)

    def delGroup(self, child):
        self.children.remove(child)
        self.childPanel.remove(child.op)
        self.childPanel.remove(child.panel)
        lp = len(self.parameters)
        lc = len(self.children)
        if lp == 0 and lc > 0:
            self.children[0].op.setVisible(False)
        if lp == 0 and lc == 0:
            self.listPanel.setVisible(False)

    def delParam(self, param):
        self.parameters.remove(param)
        self.paramPanel.remove(param.op)
        self.paramPanel.remove(param.panel)
        lp = len(self.parameters)
        lc = len(self.children)
        if lp > 0:
            self.parameters[0].op.setVisible(False)
        if lp == 0 and lc > 0:
            self.children[0].op.setVisible(False)
        if lp == 0 and lc == 0:
            self.listPanel.setVisible(False)

    def delSelf(self, sender):
        self.parent.delGroup(self)

    def invertSelf(self, sender):
        if self.isInverted:
            self.isInverted = False
            self.panel.removeStyleName('aur-search-advanced-group-inverted')
            self.op.setText(self.operator)
        else:
            self.isInverted = True
            self.panel.addStyleName('aur-search-advanced-group-inverted')
            self.op.setText(self.operator + ' not')

    def invertOperator(self, sender):
        self.operator = 'or' if self.operator == 'and' else 'and'
        for x in self.parameters:
            suffix = ' not' if x.isInverted else ''
            x.op.setText(self.operator + suffix)
        for x in self.children:
            suffix = ' not' if x.isInverted else ''
            x.op.setText(self.operator + suffix)