# Development Log

## Table of Contents
 
- [Overview](#overview)
- [6 April 2026 - Original Concept](#6-april-2026---original-concept)

## Overview

  This "journal" is used to track several aspects of the development.  I will include
an initial description, some of the notes I will feed AI.  Also this will contain the 
original concept description for this small project.

  The goal is to NOT merge the devlog with the develop or main branches.



## 6 April 2026 - Original Concept

Objective:
  This project is to develop a timewarrior extension that reports how much of
your allocation for a given project has been used.  The idea here is that you have
more than one project, or activity, to charge time to.  During the month you want to
see how much of the allocated time for a project you have used up.  This script also
would allow you to see what your allocation vs actual was for a previous month.

Thoughts about implementation:
1. Under the .timewarrior folder are other folders.  The data folder, the holiday
   folder and more.  I think I want to try and add a allocation folder.  The 
   timewarrior.cfg file would contain a reference to the allocation folder. And,
   then the allocation folder would contain an allocation for each month.

2. Monthly allocation files would have the different allocations for each project.
   Tags would be associated with an allocation.  Along with a percentage or hours would
   also be associated with each allocation.

3. The script would only work correctly if timewarrior sent a months worth of data
   to the extension script.

4. The script will be a python script that uses some of the same code as the 
   projected-vs-actual script.

5. A optional feature could be to combined time segments that aren't allocated
   to a project, to the last allocated tag on that day.  Meaning if you start
   the day with an allocated tag, and none of the time 


## 8 April 2026 - AI Prompt

This is a prompt requesting the creation of a python script that creates a works as an
extension for timewarrior.  The purpose of the extension is to figure out actual time
spent, and time remaining, on allocated 'projects' for a given month.

Here are some of the rules for the scripts behavior.
1. The script will use a folder location in the timewarrior.cfg for the allocation of
   monthly allocation files.  If the folder isn't defined then an error is returned
   and an error message displayed.  The value will be in a variable named 'allocated.folder'
   and works like the timewarrior.cfg values.
2. The script already provided is an example script, of another timewarrior
   extension python script that works under the name 'projected'.  This script will be
   given the name 'allocated'.
3. The script will look for an allocation file for the data range provided in the data
   passed to the extension.  If the extension file for the give time period doesn't 
   exist create an empty file with the file name form of 'YYYY-MM-Allocation.data'.
   If the 'allocated.folder' contains an allocation file for the previous month, copy
   the values from that file into the new file.  If the month file doesn't exist, then
   the fill in the file with a default ini TOML structure, like the one defined by you.
   The project name would be "Work", the tags would be ["Development", "Design"], with
   an allocation type of percentage and 1.00 for the percentage value.
4. When everything is setup correctly, the script takes the time span, in the data passed
   to it from timewarrior, and figures out if one of the tags, for that time span, is
   part of one of the defined projects.  If it is the time is added to the total for the
   month, if it isn't part of a project it is added to an unallocated value.
5. The script will have the added feature of being able to add, delete, or modify
   projects.  Meaning a command could add a project named 'R&D' and then the allocation
   for that project could be set along with tags added or removed from the project.
6. The script will figure out the total hours for the month, removing holidays, and
   taking into account if fridays are only 8 hours, like the projected script.  These
   totals will be used as part of the calculation of allocated vs actual.
7. The output should be similar to the output for projected.  (NOTE: I would like Gemini to give me some help with what would be the most human readable here.)

## 8 April 2026 - AI Prompt - file format research

I need an easy to manage file format for a timewarrior python extension.  The extension 
will calculate allocated vs actual time spent on different 'projects'.  Each project
can have multiple tags associated with it.  Each project can have either a percentage
of the month, or a fixed number of hours, associated with it.

What do you recommend for a easy to use file structure that python can read?

Here is an example of one of my existing timewarrior python extension script
if it can be of any help.

