import config as cfg
import os
import locale

def safe_decode(s):
    """
    Decode bytes to unicode characters safely

    Args:
        s (bytes): bytes

    Returns:
        str

    """

    _chk_config('encoding')
    try:
        decoded = s.decode(locale.getpreferredencoding())
    except UnicodeDecodeError as err:
        #logger.exception('Error in decoding: %s', err)
        decoded = s.decode(cfg.encoding, 'ignore')
    return decoded

# config #
def github_token():
    """
    Return a github access token.
    """
    _chk_config('github_access_token')
    return cfg.github_access_token

def github_user():
    """
    Return a github username.
    """
    _chk_config('github_username')
    return cfg.github_username

def data_dir():
    """
    Returns data directory, which is relative path from project root
        if defined as relative path in config.

    Returns:
        str
    """
    _chk_config('data_dir')
    return _ensure_path(cfg.data_dir, is_dir=True)


def repos_dir():
    """
    Returns repositories directory, which is relative path from project root
        if defined as relative path in config.

    Returns:
        str
    """
    _chk_config('repos_dir')
    return _ensure_path(cfg.repos_dir, is_dir=True)

def out_dir(value=None):
    """
    Returns output directory, which is relative path from project root
        if defined as relative path in config.

    Returns:
        str
    """
    _chk_config('out_dir', value)
    return _ensure_path(cfg.out_dir, is_dir=True)

def cmd_timeout():
    """
    Returns option of the timeout value for command execution
    (Default = 300)

    Returns:
        int
    """
    _chk_config('cmd_timeout')
    timeout = 300
    if getattr(cfg, 'cmd_timeout') is not None and type(cfg.cmd_timeout) is int:
        timeout = cfg.cmd_timeout
    return timeout

def escape_fname(fname):
    """
    Returns file name with escaped charactors.

    Returns:
        str
    """
    # must set the character \ as first element
    charactors = ['\\', '$', '\'', ':', '`']
    for c in charactors:
        fname = fname.replace(c, '\\' + c)
    fname = '\"' + fname + '\"'
    return fname

# Local Function #
def _ensure_path(path, is_dir=False):
    path = os.path.expanduser(path)
    if not os.path.isabs(path):
        path = os.path.join(_project_root(), path)

    if is_dir:
        directory = path
        path = path if path.endswith('/') else path + '/'
    else:
        directory = os.path.dirname(path)

    # make directories if not exist
    os.makedirs(directory, exist_ok=True)
    return path

def _project_root():
    return os.path.dirname(os.path.abspath(__file__))

def _chk_config(name, value=None):
    if not hasattr(cfg, name) or getattr(cfg, name) is None:
        cfg.load_config()
    if value is not None:
        cfg.put_config(name, value)
