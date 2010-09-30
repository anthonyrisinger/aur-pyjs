# -*- coding: utf-8 -*-
from lib.gui.core import Mediator
from lib.gui.core import Ident


class StageMediator(Mediator):

    NAME = Ident['stage']

    def onRegister(self):
        self.viewComponent.draw()

    def listNotificationInterests(self):
        return []

    def handleNotification(self, note):
        pass

    def onRemove(self):
        pass
