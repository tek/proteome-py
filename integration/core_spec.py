from kallikrein import Expectation, kf
from kallikrein.matchers import contain
from kallikrein.matchers.either import be_right

from amino.test import create_temp_file
from amino import _, Nothing, List, Path, Nil, Just
from amino.json import decode_json, dump_json

from ribosome.test.integration.klk import later

from proteome.components.core.main import BuffersState

from integration._support.base import DefaultSpec


class CoreSpec(DefaultSpec):
    '''buffer list persistence
    save two buffers and no current file $save_two_bufs
    load two buffers and no current file $load_two_bufs
    load current buffer $load_current_buf
    '''

    def setup(self) -> None:
        super().setup()
        self.f1 = str(create_temp_file('f1'))
        self.f2 = str(create_temp_file('f2'))
        self.buffers_state = BuffersState(List(self.f1, self.f2), Nothing)

    @property
    def state_file(self) -> Path:
        return self.state_dir / 'buffers.json'

    def save_two_bufs(self) -> Expectation:
        self.vim.edit(self.f1).run_sync()
        self.vim.edit(self.f2).run_sync()
        self.cmd_sync('new')
        self.cmd_sync('ProSave')
        return later(kf(lambda: decode_json((self.state_file).read_text())).must(be_right(self.buffers_state)))

    def load_two_bufs(self) -> Expectation:
        self.state_file.write_text(dump_json(self.buffers_state).get_or_raise)
        self.cmd_sync('ProLoad')
        return (
            self._buffer_count(3) &
            kf(lambda: self.vim.buffers / _.name).must(contain(self.f2)) &
            self._buffer_name('')
        )

    def load_current_buf(self) -> Expectation:
        self.state_file.write_text(dump_json(BuffersState(Nil, Just(self.f2))).get_or_raise)
        self.cmd_sync('ProLoad')
        return self._buffer_name(self.f2)

__all__ = ('CoreSpec',)
