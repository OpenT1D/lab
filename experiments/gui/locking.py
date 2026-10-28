"""A live kernel lock grants one GUI manager authority over its local journal."""

import errno
import os
import stat

from experiments.platform_files import open_regular


class WorkspaceLock:
    """Never unlink the lock inode or infer authority from saved process IDs."""

    def __init__(self, path):
        self.descriptor = None
        descriptor = open_regular(path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            opened = os.fstat(descriptor)
            current = path.lstat()
            if not stat.S_ISREG(opened.st_mode) or (
                opened.st_dev,
                opened.st_ino,
            ) != (current.st_dev, current.st_ino):
                raise ValueError("GUI manager lock must be a stable regular file")
            os.set_inheritable(descriptor, False)
            try:
                if os.name == "nt":
                    import msvcrt

                    os.lseek(descriptor, 0, os.SEEK_SET)
                    msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as error:
                if error.errno in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                    raise ValueError("Another GUI server already manages this workspace") from error
                raise
        except BaseException:
            os.close(descriptor)
            raise
        self.descriptor = descriptor

    def close(self):
        if self.descriptor is not None:
            descriptor, self.descriptor = self.descriptor, None
            if os.name == "nt":
                import msvcrt

                os.lseek(descriptor, 0, os.SEEK_SET)
                try:
                    msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
                finally:
                    os.close(descriptor)
                return
            # Closing the held descriptor releases flock without replacing its inode.
            os.close(descriptor)
