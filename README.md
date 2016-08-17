# pmacUtil
A collection of EPICS database templates and PMAC PLCs

## Using pmacUtil in conjunction with motion area JSON files
As well as providing EPICS templates and PLCs, pmacUtil implements part of the
`make` system for modules in the motion area (`/dls_sw/work/motion`).
Version 4-38 of pmacUtil introduced a change which means `dls_pmcgenerator`
is used to process any JSON files in a motion module's `src` directory when
`make` is run in the given motion module.

To enable this functionality, you should list pmacUtil version 4-38 or higher
in your motion area `configure/RELEASE` file, and you should also add an entry
`DLS_PMCGENERATOR` to the same `configure/RELEASE` file. The specified version
of `dls_pmcgenerator` will be referenced by `pmacUtil/configure/PMC_RULES` when
`make` is run in the motion module. This means `pmacUtil` and
`dls_pmcgenerator` can be versioned seperately.

This only applies to motion area RELEASE files - there is no need to add
`dls_pmcgenerator` to IOC RELEASE files.
