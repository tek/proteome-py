from typing import Tuple
from pathlib import Path
import shutil

from fn import F  # type: ignore

import asyncio
from asyncio.subprocess import PIPE  # type: ignore

from tryp import Map, List

from proteome.project import Project

from trypnv import Log


class Result(object):

    def __init__(self, success: bool, msg: str) -> None:
        self.success = success
        self.msg = msg

    def __str__(self):
        return ('subprocess finished successfully'
                if self.success
                else 'subprocess failed: {}'.format(self.msg))


class Job(object):

    def __init__(
            self,
            project: Project,
            exe: str,
            args: List[str]) -> None:
        self.project = project
        self.exe = exe
        self.args = args
        self.status = asyncio.Future()  # type: asyncio.Future

    def finish(self, f):
        err, msg = f.result()
        self.status.set_result(Result(err == 0, msg))

    def cancel(self, reason: str):
        self.status.set_result(Result(False, 'canceled: {}'.format(reason)))

    @property
    def valid(self):
        return (
            not self.status.done() and
            self.cwd.is_dir() and (
                Path(self.exe).exists or
                shutil.which(self.exe) is not None
            )
        )

    @property
    def cwd(self):
        return self.project.root

    def __str__(self):
        return 'Job({}, {}, {})'.format(self.project.name, self.exe,
                                        ' '.join(self.args))


class ProcessExecutor(object):

    def __init__(self, current: Map[Project, Job]=Map()) -> None:
        self.current = current

    @asyncio.coroutine
    def process(self, job: Job):
        return (yield from asyncio.create_subprocess_exec(  # type: ignore
            job.exe,
            *job.args,
            stdout=PIPE,
            stderr=PIPE,
            cwd=str(job.cwd),
        ))

    @asyncio.coroutine
    def execute(self, job: Job):
        proc = yield from self.process(job)
        yield from proc.wait()  # type: ignore
        err = yield from proc.stderr.readline()
        return proc.returncode, err.decode()

    def run(self, job: Job):
        ''' return values of execute are set as result of the task
        returned by ensure_future(), obtainable via task.result()
        '''
        if self._can_execute(job):
            task = asyncio.ensure_future(self.execute(job))  # type: ignore
            task.add_done_callback(job.finish)
            task.add_done_callback(F(self.job_done, job))
            self.current[job.project] = job
        else:
            Log.error('invalid execution job: {}'.format(job))
            job.cancel('invalid')
        return job

    def _can_execute(self, job: Job):
        return job.project not in self.current and job.valid

    def job_done(self, job, status):
        if job.project in self.current:
            self.current.pop(job.project)

    @property
    def ready(self):
        return self.current.is_empty

__all__ = ['Executor']
