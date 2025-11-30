import os
import sys

if sys.platform == 'win32':
    import msvcrt
else:
    import fcntl

class LockFile:
    def __init__(self, path):
        self.path = path
        self.fp = None

    def acquire(self):
        """Acquires the lock. Returns True if successful, False otherwise."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.path), exist_ok=True)

            if sys.platform == 'win32':
                self.fp = open(self.path, 'w')
                # Lock the file
                msvcrt.locking(self.fp.fileno(), msvcrt.LK_NBLCK, 1)
                self.fp.write(str(os.getpid()))
                self.fp.flush()
            else:
                self.fp = open(self.path, 'w')
                # Try to acquire an exclusive lock without blocking
                fcntl.lockf(self.fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self.fp.write(str(os.getpid()))
                self.fp.flush()
            return True
        except (IOError, OSError):
            if self.fp:
                self.fp.close()
                self.fp = None
            return False

    def release(self):
        """Releases the lock."""
        if self.fp:
            try:
                if sys.platform == 'win32':
                    msvcrt.locking(self.fp.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.lockf(self.fp, fcntl.LOCK_UN)

                self.fp.close()
                if os.path.exists(self.path):
                    os.unlink(self.path)
            except:
                pass
