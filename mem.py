from collections import defaultdict
from errno import ENOENT
from stat import S_IFDIR, S_IFLNK, S_IFREG
from sys import argv, exit
from time import time
from fuse import FUSE, FuseOSError, Operations, LoggingMixIn


class Property(dict):
    """ Default Properties of a file/directory object"""

    def __init__(self, st_mode=493, st_nlink=0, st_size=0, st_ctime='', st_mtime='', st_atime='', st_gid=0, st_uid=0):
        self.st_mode = st_mode
        self.st_nlink = st_nlink
        self.st_size = st_size
        self.st_ctime = st_ctime
        self.st_mtime = st_mtime
        self.st_atime = st_atime
        self.st_gid = st_gid
        self.st_uid = st_uid


class Directory(object):
    """ A directory object"""

    files = {}
    directories = {}
    properties = Property()

    def __init__(self, files, directories, properties):
        self.files = files
        self.directories = directories
        self.properties = properties


class File(object):
    """ A file object"""

    data = b''
    properties = Property()

    def __init__(self, data, properties):
        self.data = data
        self.properties = properties


class Memory(LoggingMixIn, Operations):
    """Example memory filesystem. Supports only one level of files."""

    def __unicode__(self):
        return str(self)

    def __init__(self):
        self.filesystem = {}
        self.fd = 0
        now = time()
        self.filesystem['/'] = Directory(files={}, directories={}, properties=Property(
            st_mode=S_IFDIR | 493, st_nlink=2, st_size=0, st_ctime=time(), st_mtime=time(), st_atime=time(), st_gid=0, st_uid=0))

    def chmod(self, path, mode):
        item = self.getFile(path)
        if not item:
            item = self.getDir(path)
        if item:
            item.properties.st_mode &= 258048
            item.properties.st_mode |= mode
        return 0

    def chown(self, path, uid, gid):
        item = self.getFile(path)
        if not item:
            item = self.getDir(path)
        if item:
            item.properties.st_uid = uid
            item.properties.st_gid = gid
        return 0

    def create(self, path, mode):
        filename = path.split('/')[-1]
        dirname = '/'.join(path.split('/')[:-1])
        dirobj = self.getDir(dirname)
        dirobj.files[filename] = File(data=b'', properties=Property(
            st_mode=S_IFREG | mode, st_nlink=1, st_size=0, st_ctime=time(), st_mtime=time(), st_atime=time()))
        self.fd += 1
        return self.fd

    def getattr(self, path, fh=None):
        st = self.getFile(path)
        if not st:
            st = self.getDir(path)
        if not st:
            raise FuseOSError(ENOENT)
        return st.properties.__dict__

    def getxattr(self, path, name, position=0):
        st = self.getFile(path)
        if not st:
            st = self.getDir(path)
        attrs = st.properties.get('attrs', {})
        try:
            return attrs[name]
        except KeyError:
            return ''

    def listxattr(self, path):
        st = self.getFile(path)
        if not st:
            st = self.getDir(path)
        attrs = st.properties.get('attrs', {})
        return list(attrs.keys())

    def mkdir(self, path, mode):
        path = path.rstrip('/')
        newdir = path.split('/')[-1]
        dirname = '/'.join(path.split('/')[:-1])
        dirobj = self.getDir(dirname)
        dirobj.directories[newdir] = Directory(files={}, directories={}, properties=Property(
            st_mode=S_IFDIR | mode, st_nlink=2, st_size=0, st_ctime=time(), st_mtime=time(), st_atime=time()))
        dirobj.properties.st_nlink += 1

    def open(self, path, flags):
        self.fd += 1
        return self.fd

    def read(self, path, size, offset, fh):
        fileobj = self.getFile(path)
        return fileobj.data[offset:(offset + size)]

    def readdir(self, path, fh):
        st = self.getDir(path)
        return ['.', '..'] + [x for x in st.files] + [x for x in st.directories]

    def readlink(self, path):
        st = self.getFile(path)
        return st.data

    def removexattr(self, path, name):
        st = self.getFile(path)
        if not st:
            st = self.getDir(path)
        attrs = st.properties.get('attrs', {})
        try:
            del attrs[name]
        except KeyError:
            pass

    def rename(self, old, new):
        oldname = old.split('/')[-1]
        newname = new.split('/')[-1]
        parentname = '/'.join(old.split('/')[:-1])
        parentobj = self.getDir(parentname)
        if self.getFile(old):
            parentobj.files[newname] = parentobj.files.pop(oldname)
        elif self.getDir(old):
            parentobj.directories[newname] = parentobj.directories.pop(oldname)

    def rmdir(self, path):
        parentname = '/'.join(path.split('/')[:-1])
        parentobj = self.getDir(parentname)
        dirname = path.split('/')[-1]
        parentobj.directories.pop(dirname)
        parentobj.properties.st_nlink -= 1

    def setxattr(self, path, name, value, options, position=0):
        st = self.getFile(path)
        if not st:
            st = self.getDir(path)
        attrs = st.setdefault('attrs', {})
        attrs[name] = value

    def statfs(self, path):
        return dict(f_bsize=512, f_blocks=4096, f_bavail=2048)

    def symlink(self, target, source):
        targetname = target.split('/')[-1]
        targetdir = '/'.join(target.split('/')[:-1])
        targetdirobj = self.getDir(targetdir)

        targetdirobj.files[targetname] = File(data=source, properties=Property(
            st_mode=S_IFLNK, st_nlink=1, st_size=len(source), st_ctime=time(), st_mtime=time(), st_atime=time()))

    def truncate(self, path, length, fh=None):
        st = self.getFile(path)
        st.data = st.data[:length]
        st.properties.st_size = length

    def unlink(self, path):
        dirname = '/'.join(path.split('/')[:-1])
        filename = path.split('/')[-1]
        st = self.getDir(dirname)
        st.files.pop(filename)

    def utimens(self, path, times=None):
        now = time()
        (atime, mtime,) = times if times else (now, now)
        st = self.getFile(path)
        st.properties.st_atime = atime
        st.properties.st_mtime = mtime

    def write(self, path, data, offset, fh):
        st = self.getFile(path)
        st.data = st.data[:offset] + data
        st.properties.st_size = len(st.data)
        return len(data)

    def getFile(self, path):
        if path[-1] == '/':
            return None
        else:
            patharray = path.split('/')
            filename = patharray.pop()
            dirname = '/'.join(path.split('/')[:-1])
            location = self.getDir(dirname)
            if location and filename in location.files:
                return location.files[filename]
            return None

    def getDir(self, path):
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
    fuse = FUSE(Memory(), argv[1], foreground=True)#, debug=True)
