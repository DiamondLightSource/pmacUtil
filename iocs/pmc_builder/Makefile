# This is a top level makefile that can make all sub directories
DIRS = $(wildcard ?????-MO-STEP-??)

install:
	for d in $(DIRS); do $(MAKE) -C $$d || exit 1; done

clean:
	for d in $(DIRS) ; do $(MAKE) -C $$d clean || exit 1; done
