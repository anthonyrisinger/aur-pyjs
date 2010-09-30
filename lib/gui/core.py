# -*- coding: utf-8 -*-
import puremvc.patterns.facade
import puremvc.patterns.command
import puremvc.patterns.proxy
import puremvc.patterns.mediator


def main():
    Facade.getInstance().sendNotification(
        Note.INIT,
        StageComponent.get_instance()
    )


class App(object):

    NAME = 'aur'

    AUTHOR = [
        ('C Anthony Risinger', 'Contact Anthony', 'mailto:anthony@extof.me'),
    ]

    #COPYRIGHT = [
    #    ('Judd Vinet', 'Contact Judd', 'mailto:jvinet@zeroflux.org'),
    #    ('Aaron Griffin', 'Contact Aaron', 'mailto:aaron@archlinux.org'),
    #]

    COPYRIGHT = [
        ('XXXXXX', 'Contact XXXXXX', '#XXXXXX'),
        ('XXXXXX', 'Contact XXXXXX', '#XXXXXX'),
    ]

    VERSION = '0.1'

    VERSION_INFO = (0, 1, 0, 'alpha', 0)


class Facade(puremvc.patterns.facade.Facade):

    def initializeController(self):
        from lib.gui.controller import core
        super(self.__class__, self).initializeController()
        self.registerCommand(Note.INIT, core.InitCommand)

    @classmethod
    def getInstance(cls):
        return cls.instance or cls()


class SimpleCommand(puremvc.patterns.command.SimpleCommand):

    pass


class MacroCommand(puremvc.patterns.command.MacroCommand):

    pass


class Proxy(puremvc.patterns.proxy.Proxy):

    pass


class Mediator(puremvc.patterns.mediator.Mediator):

    pass


class StageComponent(object):

    instance = None

    component = None

    def __new__(cls, *args, **kwargs):
        if cls.instance is None:
            if cls.component is None:
                from lib.gui.view.component import core
                cls.set_component(core.StageComponent)
            cls.instance = cls.component(*args, **kwargs)
        return cls.instance

    @classmethod
    def get_instance(cls):
        return cls.instance or cls()

    @classmethod
    def set_component(cls, component):
        cls.component = component


class _Name(object):

    sep = '_'

    def __init__(self, name):
        super(self.__class__, self).__setattr__('NAME', name.upper())
        super(self.__class__, self).__setattr__('attr', {})

    def __len__(self):
        return len(self.attr)

    def __contains__(self, name):
        if name.upper() in self.attr:
            return True
        return False

    def __getitem__(self, name):
        name = name.upper()
        if name == 'NAME':
            raise TypeError('NAME is reserved')
        attr = self.attr.get(name)
        if attr is None:
            attr = type(self)(self.sep.join((self.NAME, name)))
            super(self.__class__, self).__setattr__(name, attr)
        return attr

    def __delitem__(self, name):
        #TODO also remove notifications from facade?
        name = name.upper()
        if name == 'NAME':
            raise TypeError('NAME is reserved')
        if name in self.attr:
            del self.attr[name]
            super(self.__class__, self).__delattr__(name)

    def __setattr__(self, name, value):
        raise TypeError('Attribute setting not allowed')

    def __delattr__(self, name):
        raise TypeError('Attribute deleting not allowed')

    def __hash__(self):
        return hash(self.NAME)

    def __cmp__(self, other):
        if self.NAME == other.NAME:
            return 0
        return 1


Name = _Name(App.NAME)
Ident = Name['ident']
Note = Name['note']
