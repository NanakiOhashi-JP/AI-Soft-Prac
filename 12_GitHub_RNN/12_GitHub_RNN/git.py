import os
import re
from urllib.parse import urlparse

from cmdexec import CommandError, exec_cmd
from util import safe_decode, repos_dir, escape_fname

class Repository:

    def __init__(self, remote_url):
        """
        Initialize parameters

        Args:
            remote_url (str): remote url
        """
        parse_res = urlparse(remote_url)
        # remove prefix `/`
        repo_name = parse_res.path[1:]
        if remote_url.endswith('.git'):
            # remove `.git`
            repo_name = repo_name[:-4]

        self.remote_url = remote_url
        self.name = repo_name

    @property
    def repo_dir(self):
        return os.path.join(repos_dir(), self.name)

    def _exec_cmd(self, cmd, env=None, cwd=None, expire=True, **kwargs):
        if cwd is None:
            cwd = self.repo_dir
        git_cmd = 'git --no-pager '
        git_cmd += cmd

        try:
            cp = exec_cmd(cmd=git_cmd, env=env, cwd=cwd, expire=False, **kwargs)
        except CommandError as err:
            raise err

        return cp

    def is_cloned(self):
        """
        Returns if the repository has been already cloned.

        Returns:
            bool
        """
        if not os.path.exists(self.repo_dir):
            return False

        cmd = 'rev-parse --is-inside-work-tree'
        try:
            cp = self._exec_cmd(cmd=cmd, expire=False)
        except CommandError:
            return False

        return cp.stdout.decode().strip() == 'true'

    def clone(self, options=None):
        """
        Clone the repository

        Args:
            options (list of str, optional): options for `git-clone`
        Returns:
            bool: return true if successfully cloned
        """

        if self.is_cloned():
            return False

        cmd = 'clone {} {}'.format(self.remote_url, self.name)
        if options is not None:
            cmd += options
        try:
            self._exec_cmd(cmd=cmd, cwd=repos_dir(), expire=False)
        except CommandError as err:
            return False

        return True


    def _split_hash_date_message(self, stdout):
        # the line format is commit id + datetime + message like '7309ea39a637e877ede5156b5c85c47cc87dd66b', ' Fri Feb 14 14:47:19 2014 +0100', 'Restore log message tag 02636, assign unique tags.'
        return (line.split(',', 2) for line in stdout.decode().strip().split('\n'))

    def all_commit_hashes(self):
        """
        List commit hashes in order of oldest

        Returns:
            generator of commit hash and datetime
        """

        assert self.is_cloned()
        cmd = 'log --reverse --format="%H, %cd, %s"'
        cp = self._exec_cmd(cmd)
        return self._split_hash_date_message(cp.stdout)

    def get_parent_hashes(self, commit_hash):
        """
        Returns parent commit hash for given commit hash

        Args:
            commit_hash (str): target commit hash
        Returns:
            list of commit hash
        """

        assert self.is_cloned()
        cmd = 'show --no-patch --format=%P {}'.format(commit_hash)
        cp = self._exec_cmd(cmd)
        return cp.stdout.decode().strip().split()

    def all_main_branch_hashes(self):
        """
        List commit hashes in order of oldest (main branch only)

        Returns:
            generator of commit hash and datetime
        """
        assert self.is_cloned()
        cmd = 'log --first-parent --reverse --format="%H, %cd, %s"'
        cp = self._exec_cmd(cmd)
        return self._split_hash_date_message(cp.stdout)

    def get_file_content(self, commit_hash, file, decode=True):
        """
        Returns the content of given file on the commit hash.

        Args:
            commit_hash (str): target commit hash
            file (str): relative path from repository root
            decode: the flag whether the decoding is needed or not
        Returns:
            str or byte (if decode is False)
        """

        assert self.is_cloned()
        cmd = 'show {}:{}'.format(commit_hash, escape_fname(file))
        try:
            cp = self._exec_cmd(cmd)
        except CommandError:
            return ""

        if decode:
            out = safe_decode(cp.stdout)
        else:
            out = cp.stdout
        
        return out

    def get_all_files(self, commit_hash):
        """
        Lists all files on given commit hash.

        Args:
            commit_hash (str): target commit files
        Returns:
            list of str: all files
        """
        assert self.is_cloned()
        # get all files in the commit
        cmd = 'ls-tree --name-only -r {}'.format(commit_hash)
        cp = self._exec_cmd(cmd)
        all_files = safe_decode(cp.stdout).strip().split('\n')

        return [] if all_files == [''] else all_files

    def get_changed_files(self, commit_hash1, commit_hash2):
        """
        Lists changed files between commit hashs.

        Args:
            commit_hash1 (str): target commit files
            commit_hash2 (str): target commit files
        Returns:
            list of str: changed files
        """
        assert self.is_cloned()
        if commit_hash1 is not None and commit_hash2 is not None:
            # -r: recurse into subdirectories
            # -name-status: Show only names and status of changed files.
            #               'A' means added, 'M' means modified.
            # --histogram: use histogram diff algorithm 
            # -M100%: Detect renames (To limit detection to exact renames, use -M100%)
            #cmd = 'diff --stat --name-status --diff-filter=d -M100% '
            cmd = 'diff-tree --no-commit-id --name-status --histogram -M100% '
            cmd += '-r {} {}'.format(commit_hash1, commit_hash2)
            cp = self._exec_cmd(cmd)
            files = safe_decode(cp.stdout).strip().split('\n')
            changed_files = [file[2:] for file in files if not file.startswith('R')]
        else:
            commit_hash = commit_hash1 if commit_hash2 is None else commit_hash2
            # get all files in the commit
            changed_files = self.get_all_files(commit_hash)

        return [] if changed_files == [''] else changed_files

    def file_stat(self, commit_hash1, commit_hash2, file):
        """
        Returns the number of added/deleted lines from given commit hash1 to given commit hash2.

        Args:
            commit_hash1 (str): "from" commit hash, if this is None indicates comparing to initial state (empty)
            commit_hash2 (str): "to" commit hash
            file (str):

        Returns:
            (int, int): number of added lines, number of deleted lines
        """
        if commit_hash1 is None:
            commit_hash1 = '4b825dc642cb6eb9a060e54bf8d69288fbee4904' # means initial state of repository

        cmd = 'diff --numstat --histogram {} {} --  {}'.format(commit_hash1, commit_hash2, escape_fname(file))
        cp = self._exec_cmd(cmd)
        # line 1: commit hash, line 2: empty line, line 3: target line
        try:
            line = safe_decode(cp.stdout).strip().split('\n')[0]
        except IndexError as err:
            from common.log import progress_log
            progress_log("IndexError: {0} {1} cmd: {2} file: {3} escaped: {4}.\n".format(commit_hash1, commit_hash2, cmd, file, escape_fname(file)))
            raise err
        addition, deletion, _ = re.split(r'\s', line, 2)

        addition = 0 if addition == '-' else int(addition)
        deletion = 0 if deletion == '-' else int(deletion)
        return addition, deletion

