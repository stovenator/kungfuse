kungfuse
========

A FusePy based in memory filesystem

Based on FusePY memory example here: https://github.com/terencehonles/fusepy/blob/master/examples/memory.py

Usage:
    mkdir /mnt/mountpoint
    python mem.py /mnt/mountpoint


TODO:
    Lots of Error handling
    rmdir - don't remove if the directory isn't empty
    Permissions - Seems to ignore the permissions completely
    Fix symlinks:
        Broken when only directory given for source file
        Broken when full path not given for target
    Hard links?
    Better Documentation
    
    
