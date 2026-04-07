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

