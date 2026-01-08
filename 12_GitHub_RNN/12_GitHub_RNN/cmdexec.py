import os,sys
import subprocess
import signal
from subprocess import PIPE
#import timeout_decorator

from util import safe_decode, escape_fname, cmd_timeout


class CommandError(Exception):
    """Thrown if execution of the command fails."""

    def __init__(self, cmd, completed_process=None):
        """
        Initialize parameters
        Args:
            cmd (str):
            completed_process (subprocess.CompletedProcess):
        """

        self.cmd = cmd
        self.cp = completed_process

        msg = '{} failed'.format(self.cmd)
        if self.cp is not None:
            status = self.cp.returncode
            stdout = safe_decode(self.cp.stdout)
            stderr = safe_decode(self.cp.stderr)
            msg += ', exit status: {}'.format(status)
            msg += ', stdout: {}'.format(stdout)
            msg += ', stderr: {}'.format(stderr)

        super(CommandError, self).__init__(msg)


def exec_cmd(cmd, env=None, cwd=None, stdout=PIPE, stderr=PIPE, expire=True, **kwargs):
    """
    Execute shell commands

    Args:
        cmd (str or list): executable and its args
        env (dict of str: str): optional environment variables
        cwd (str): current working directory, optional
        stdout (int): defaults to subprocess.PIPE
        stderr (int): defaults to subprocess.PIPE
        expire (boolean): whether expiration of execution is needed or not
        **kwargs: parameters passed into subprocess.run method.
    Returns:
        subprocess.CompletedProcess
    Raises:
        CommandError
        TimeoutExpired

    Do we need to use timeout_decorator ?
    """

    inline_env = env
    env = os.environ.copy()
    env["LANGUAGE"] = "C"
    env["LC_ALL"] = "C"
    if inline_env:
        env.update(inline_env)
    is_shell = True if type(cmd) is str else False

    env_str = [key + '=' + value for key, value in env.items()]
    #logger.debug('command: %s, env: %s, cwd: %s', cmd, ','.join(env_str), cwd)
    try:
        proc = subprocess.Popen(cmd, env=env, cwd=cwd, stdout=stdout, stderr=stderr, shell=is_shell, **kwargs)
        timeout = None if not expire else cmd_timeout()
        # set timeout for command execution
        outs, errs = proc.communicate(timeout=timeout)
        cp = subprocess.CompletedProcess(args=cmd, returncode=proc.returncode, stdout=outs, stderr=errs)
    except subprocess.TimeoutExpired as err:
        #os.kill(proc.pid, signal.SIGTERM)
        proc.kill()
        outs, errs = proc.communicate()
        raise err

    if cp.returncode != 0:
        raise CommandError(cmd, cp)
    return cp
