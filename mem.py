import errno
import stat
import time
import os
from fuse import FUSE, FuseOSError, Operations, LoggingMixIn

class Property(dict):
    def __init__(self, st_mode=493, st_nlink=0, st_size=0, st_ctime=0, st_mtime=0, st_atime=0, st_gid=0, st_uid=0, st_blocks=0):
        self.st_mode = st_mode
        self.st_nlink = st_nlink
        self.st_size = st_size
        self.st_ctime = st_ctime
        self.st_mtime = st_mtime
        self.st_atime = st_atime
        self.st_gid = os.getgid()
        self.st_uid = os.getuid()
        self.st_blocks = st_blocks

class Directory(object):
    def __init__(self, files, directories, properties):
        self.files = files
        self.directories = directories
        self.properties = properties

class File(object):
    def __init__(self, data, properties):
        self.data = data
        self.properties = properties


class Memory(LoggingMixIn, Operations):

    def __unicode__(self):
        return str(self)

    def __init__(self):
        self.filesystem = {}
        self.fd = 0
        now = time.time()
        self.filesystem['/'] = Directory(files={}, directories={}, properties=Property(
            st_mode=stat.S_IFDIR | 493, st_nlink=2, st_size=0, st_ctime=now, st_mtime=now, st_atime=now, st_gid=os.getgid(), st_uid=os.getuid()))

    def chmod(self, path, mode):
        item = self.get_file(path)
        if not item:
            item = self.get_dir(path)
        if item:
            item.properties.st_mode &= 258048
            item.properties.st_mode |= mode
        return 0

    def chown(self, path, uid, gid):
        item = self.get_file(path)
        if not item:
            item = self.get_dir(path)
        if item:
            item.properties.st_uid = uid
            item.properties.st_gid = gid
        return 0

    def create(self, path, mode):
        filename = path.split('/')[-1]
        dirname = '/'.join(path.split('/')[:-1])
        dirobj = self.get_dir(dirname)
        now = time.time()
        dirobj.files[filename] = File(data=bytearray(), properties=Property(
            st_mode=stat.S_IFREG | mode, st_nlink=1, st_size=0, st_ctime=now, st_mtime=now, st_atime=now))
        self.fd += 1
        return self.fd

    def getattr(self, path, fh=None):
        st = self.get_file(path)
        if not st:
            st = self.get_dir(path)
        if not st:
            raise FuseOSError(errno.ENOENT)
        return st.properties.__dict__

    def getxattr(self, path, name, position=0):
        st = self.get_file(path)
        if not st:
            st = self.get_dir(path)
        attrs = st.properties.get('attrs', {})
        try:
            return attrs[name]
        except KeyError:
            return b''

    def listxattr(self, path):
        st = self.get_file(path)
        if not st:
            st = self.get_dir(path)
        attrs = st.properties.get('attrs', {})
        return list(attrs.keys())

    def mkdir(self, path, mode):
        path = path.rstrip('/')
        newdir = path.split('/')[-1]
        dirname = '/'.join(path.split('/')[:-1])
        dirobj = self.get_dir(dirname)
        now = time.time()
        dirobj.directories[newdir] = Directory(files={}, directories={}, properties=Property(
            st_mode=stat.S_IFDIR | mode, st_nlink=2, st_size=0, st_ctime=now, st_mtime=now, st_atime=now))
        dirobj.properties.st_nlink += 1

    def open(self, path, flags):
        self.fd += 1
        return self.fd

    def read(self, path, size, offset, fh):
        fileobj = self.get_file(path)
        return bytes(fileobj.data[offset:(offset + size)])

    def readdir(self, path, fh):
        st = self.get_dir(path)
        return ['.', '..'] + [x for x in st.files] + [x for x in st.directories]

    def readlink(self, path):
        st = self.get_file(path)
        return st.data

    def removexattr(self, path, name):
        st = self.get_file(path)
        if not st:
            st = self.get_dir(path)
        attrs = st.properties.get('attrs', {})
        try:
            del attrs[name]
        except KeyError:
            pass

    def rename(self, old, new):
        oldname = old.split('/')[-1]
        newname = new.split('/')[-1]
        parentname = '/'.join(old.split('/')[:-1])
        parentobj = self.get_dir(parentname)
        if self.get_file(old):
            parentobj.files[newname] = parentobj.files.pop(oldname)
        elif self.get_dir(old):
            parentobj.directories[newname] = parentobj.directories.pop(oldname)

    def rmdir(self, path):
        parentname = '/'.join(path.split('/')[:-1])
        parentobj = self.get_dir(parentname)
        dirname = path.split('/')[-1]
        parentobj.directories.pop(dirname)
        parentobj.properties.st_nlink -= 1

    def setxattr(self, path, name, value, options, position=0):
        st = self.get_file(path)
        if not st:
            st = self.get_dir(path)
        attrs = st.setdefault('attrs', {})
        attrs[name] = value

    def statfs(self, path):
        return dict(f_bsize=512, f_blocks=4096, f_bavail=2048)

    def symlink(self, target, source):
        targetname = target.split('/')[-1]
        targetdir = '/'.join(target.split('/')[:-1])
        targetdirobj = self.get_dir(targetdir)
        now = time.time()
        targetdirobj.files[targetname] = File(data=source, properties=Property(
            st_mode=stat.S_IFLNK, st_nlink=1, st_size=len(source), st_ctime=now, st_mtime=now, st_atime=now, st_blocks=len(source) // 512))

    def truncate(self, path, length, fh=None):
        st = self.get_file(path)
        st.data = st.data[:length]
        st.properties.st_size = length
        st.properties.st_blocks = length // 512

    def unlink(self, path):
        dirname = '/'.join(path.split('/')[:-1])
        filename = path.split('/')[-1]
        st = self.get_dir(dirname)
        st.files.pop(filename)

    def utimens(self, path, times=None):
        now = time.time()
        (atime, mtime,) = times if times else (now, now)
        st = self.get_file(path)
        st.properties.st_atime = atime
        st.properties.st_mtime = mtime

    def write(self, path, data, offset, fh):
        st = self.get_file(path)
        st.data[offset:] = data
        st.properties.st_size = len(st.data)
        st.properties.st_blocks = len(st.data) // 512
        return len(data)

    def get_file(self, path):
        if path[-1] == '/':
            return None
        else:
            patharray = path.split('/')
            filename = patharray.pop()
            dirname = '/'.join(path.split('/')[:-1])
            location = self.get_dir(dirname)
            if location and filename in location.files:
                return location.files[filename]
            return None

    def get_dir(self, path):
        path = path.rstrip('/')
        patharray = path.split('/')
        if len(patharray) <= 1:
            return self.filesystem['/']
        patharray.pop(0)
        location = self.filesystem['/']
        while patharray:
            dirpath = patharray.pop(0)
            if dirpath in location.directories:
                location = location.directories[dirpath]
            else:
                return None
        return location


if __name__ == '__main__':
    import sys
    if sys.argv[0] == 'mem.py':
        fuse = FUSE(Memory(), sys.argv[1], foreground=True, debug=True)
