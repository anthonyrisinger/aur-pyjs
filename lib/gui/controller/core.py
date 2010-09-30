# -*- coding: utf-8 -*-
from lib.gui.core import SimpleCommand
from lib.gui.core import Note
from lib.gui.view.core import StageMediator


class InitCommand(SimpleCommand):

    NAME = Note['init']

    def execute(self, note):
        self.facade.registerMediator(
            StageMediator(viewComponent=note.getBody())
        )
