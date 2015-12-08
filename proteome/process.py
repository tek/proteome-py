from typing import Tuple, Callable
from pathlib import Path
import shutil

from fn import F  # type: ignore

import asyncio
from asyncio.subprocess import PIPE  # type: ignore

from tryp import Map, List, Future

from proteome.project import Project

from trypnv import Log


class Result(object):

    def __init__(self, job: 'Job', success: bool, out: str, err: str) -> None:
        self.job = job
        self.success = success
        self.out = out
        self.err = err

    def __str__(self):
        return ('subprocess finished successfully'
                if self.success
                else 'subprocess failed: {} ({})'.format(self.msg, self.job))

    @property
    def msg(self):
        return self.err if self.err else self.out


class Job(object):

    def __init__(
            self,
            project: Project,
            exe: str,
            args: List[str]) -> None:
        self.project = project
        self.exe = exe
        self.args = args
        self.status = Future()  # type: Future

    def finish(self, f):
        code, out, err = f.result()
        self.status.set_result(Result(self, code == 0, out, err))

    def cancel(self, reason: str):
        self.status.set_result(
            Result(self, False, '', 'canceled: {}'.format(reason)))

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

    def __init__(self) -> None:
        self.current = Map()  # type: Map[Project, Job]

    async def process(self, job: Job):
        return await asyncio.create_subprocess_exec(
            job.exe,
            *job.args,
            stdout=PIPE,
            stderr=PIPE,
            cwd=str(job.cwd),
        )

    async def execute(self, job: Job):
        try:
            proc = await self.process(job)
            await proc.wait()  # type: ignore
            out = await proc.stdout.read()
            err = await proc.stderr.read()
            return proc.returncode, out.decode(), err.decode()
        except Exception as e:
            return -111, '', 'exception: {}'.format(e)

    def run(self, job: Job) -> Future[Result]:
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
        return job.status

    def _can_execute(self, job: Job):
        return job.project not in self.current and job.valid

    def job_done(self, job, status):
        if job.project in self.current:
            self.current.pop(job.project)

    @property
    def ready(self):
        return self.current.is_empty

__all__ = ['Executor']
