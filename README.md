kungfuse
========

A FusePy based in memory filesystem

Requirements:

	FusePy - https://github.com/terencehonles/fusepy
	Python 3.6 is known to work. 
	Other Python versions may work
	
Inspiration:
	
    Based on memory.py in the fusepy examples

Usage:

    mkdir /mnt/mountpoint
    python mem.py /mnt/mountpoint


TODO:

    []Lots of Error handling to be added
    []rmdir - don't remove if the directory isn't empty
    []Permissions - Seems to ignore the permissions completely
    []Fix symlinks:
        []Broken when only directory given for source file
        []Broken when full path not given for target
    []Hard links?
    []Better Documentation
    
