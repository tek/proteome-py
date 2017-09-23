from amino import List

from integration._support.base import DefaultSpec


class NavSpec(DefaultSpec):
    '''cycle through and select projects $navigate
    '''

    @property
    def components(self):
        return List('proteome.plugins.config')

    def navigate(self):
        self.cmd_sync('ProNext')
        self.project_becomes(self.name2)
        self.cmd_sync('ProTo 0')
        self.project_becomes(self.name1)
        self.cmd_sync('ProPrev')
        return self.project_becomes(self.name2)

__all__ = ('NavSpec',)
