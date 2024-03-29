from amino import List

from integration._support.base import ProteomePluginIntegrationSpec


class ShowSpec(ProteomePluginIntegrationSpec):

    @property
    def components(self):
        return List('proteome.components.config')

    def show(self):
        self._project_becomes(self.name1)
        self.vim.cmd('ProShow')
        self._wait_for(lambda: self._log_out.lift(-3).contains('Projects:'))
        lines = self._log_out[-2:]
        lines[0].should.start_with(self.ident1)
        lines[1].should.start_with(self.ident2)

__all__ = ('ShowSpec',)
