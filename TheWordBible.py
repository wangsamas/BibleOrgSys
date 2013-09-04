#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# TheWordBible.py
#   Last modified: 2013-09-04 by RJH (also update ProgVersion below)
#
# Module handling "theWord" Bible module files
#
# Copyright (C) 2013 Robert Hunt
# Author: Robert Hunt <robert316@users.sourceforge.net>
# License: See gpl-3.0.txt
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Module reading and loading theWord Bible files.
These can be downloaded from: http://www.theword.net/index.php?downloads.modules

A theWord Bible module file has one verse per line (KJV versification)
    OT (.ot file) has 23145 lines
    NT (.nt file) has 7957 lines
    Bible (.ont file) has 31102 lines.

Some basic HTML-style tags are recognised: <u></u>, <i></i>, <b></b>, <s></s>, <br>, <p>, <sup></sup>, <sub></sub>

Also, custom tags:
    <FI><Fi> for added words
    <CL> = new line (usually at the end of lines)
    <CM> = new paragraph (usually at the end of lines)

e.g.,
    In the beginning of God's preparing the heavens and the earth--
    the earth hath existed waste and void, and darkness <FI>is<Fi> on the face of the deep, and the Spirit of God fluttering on the face of the waters,<CM>
    and God saith, `Let light be;' and light is.
    And God seeth the light that <FI>it is<Fi> good, and God separateth between the light and the darkness,
    and God calleth to the light `Day,' and to the darkness He hath called `Night;' and there is an evening, and there is a morning--day one.<CM>
    And God saith, `Let an expanse be in the midst of the waters, and let it be separating between waters and waters.'
    And God maketh the expanse, and it separateth between the waters which <FI>are<Fi> under the expanse, and the waters which <FI>are<Fi> above the expanse: and it is so.
    And God calleth to the expanse `Heavens;' and there is an evening, and there is a morning--day second.<CM>
"""

ProgName = "theWord Bible format handler"
ProgVersion = "0.15"
ProgNameVersion = "{} v{}".format( ProgName, ProgVersion )

debuggingThisModule = False


import logging, os, re
from gettext import gettext as _
import multiprocessing

import Globals
from USFMMarkers import oftenIgnoredIntroMarkers, removeUSFMCharacterField, replaceUSFMCharacterFields
from BibleOrganizationalSystems import BibleOrganizationalSystem


BOS = BibleOrganizationalSystem( "GENERIC-KJV-66-ENG" )


filenameEndingsToAccept = ('.OT','.NT','.ONT','.OTX','.NTX','.ONTX',) # Must be UPPERCASE
#filenameEndingsToIgnore = ('.ZIP.GO', '.ZIP.DATA',) # Must be UPPERCASE
#extensionsToIgnore = ('ZIP', 'BAK', 'LOG', 'HTM','HTML', 'XML', 'OSIS', 'USX', 'STY', 'LDS', 'SSF', 'VRS', 'ASC', 'CSS',) # Must be UPPERCASE


# These are the verses per book in the traditional KJV versification (but only for the 66 books)
#       (They must precede the Bible import)
theWordOTBookCount = 39
theWordOTBooks = ( 'GEN', 'EXO', 'LEV', 'NUM', 'DEU', 'JOS', 'JDG', 'RUT', 'SA1', 'SA2', 'KI1', 'KI2', 'CH1', 'CH2',
                    'EZR', 'NEH', 'EST', 'JOB', 'PSA', 'PRO', 'ECC', 'SNG', 'ISA', 'JER', 'LAM', 'EZK', 'DAN', 'HOS',
                    'JOL', 'AMO', 'OBA', 'JNA', 'MIC', 'NAH', 'HAB', 'ZEP', 'HAG', 'ZEC', 'MAL', )
assert( len( theWordOTBooks ) == theWordOTBookCount )
theWordOTTotalLines = 23145
theWordOTBookLines = ( 1533, 1213, 859, 1288, 959, 658, 618, 85, 810, 695, 816, 719, 942, 822, 280, 406, 167, 1070, 2461,
                        915, 222, 117, 1292, 1364, 154, 1273, 357, 197, 73, 146, 21, 48, 105, 47, 56, 53, 38, 211, 55 )
assert( len( theWordOTBookLines ) == theWordOTBookCount )
total=0
for count in theWordOTBookLines: total += count
assert( total == theWordOTTotalLines )

theWordNTBookCount = 27
theWordNTBooks = ( 'MAT', 'MRK', 'LUK', 'JHN', 'ACT', 'ROM', 'CO1', 'CO2', 'GAL', 'EPH', 'PHP', 'COL', 'TH1', 'TH2',
                        'TI1', 'TI2', 'TIT', 'PHM', 'HEB', 'JAM', 'PE1', 'PE2', 'JN1', 'JN2', 'JN3', 'JDE', 'REV', )
assert( len( theWordNTBooks ) == theWordNTBookCount )
theWordNTTotalLines = 7957
theWordNTBookLines = ( 1071, 678, 1151, 879, 1007, 433, 437, 257, 149, 155, 104, 95, 89, 47, 113, 83, 46, 25, 303, 108, 105, 61, 105, 13, 14, 25, 404 )
assert( len( theWordNTBookLines ) == theWordNTBookCount )
total=0
for count in theWordNTBookLines: total += count
assert( total == theWordNTTotalLines )

theWordBookCount = 66
theWordTotalLines = 31102
theWordBooks = theWordOTBooks + theWordNTBooks
assert( len( theWordBooks ) == theWordBookCount )
theWordBookLines = theWordOTBookLines + theWordNTBookLines
assert( len( theWordBookLines ) == theWordBookCount )
total=0
for count in theWordBookLines: total += count
assert( total == theWordTotalLines )


def TheWordBibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False ):
    """
    Given a folder, search for theWord Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of Bibles found.

    if autoLoad is true and exactly one theWord Bible is found,
        returns the loaded theWordBible object.
    """
    if Globals.verbosityLevel > 2: print( "TheWordBibleFileCheck( {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad ) )
    if Globals.debugFlag: assert( givenFolderName and isinstance( givenFolderName, str ) )
    if Globals.debugFlag: assert( autoLoad in (True,False,) )

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("TheWordBibleFileCheck: Given '{}' folder is unreadable").format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("TheWordBibleFileCheck: Given '{}' path is not a folder").format( givenFolderName ) )
        return False

    # Find all the files and folders in this folder
    if Globals.verbosityLevel > 3: print( " TheWordBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
    foundFolders, foundFiles = [], []
    for something in os.listdir( givenFolderName ):
        somepath = os.path.join( givenFolderName, something )
        if os.path.isdir( somepath ): foundFolders.append( something )
        elif os.path.isfile( somepath ):
            somethingUpper = something.upper()
            somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
            #ignore = False
            #for ending in filenameEndingsToIgnore:
                #if somethingUpper.endswith( ending): ignore=True; break
            #if ignore: continue
            #if not somethingUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
            if somethingUpperExt in filenameEndingsToAccept:
                foundFiles.append( something )
    if '__MACOSX' in foundFolders:
        foundFolders.remove( '__MACOSX' )  # don't visit these directories

    # See if there's an theWordBible project here in this given folder
    numFound = 0
    looksHopeful = False
    lastFilenameFound = None
    for thisFilename in sorted( foundFiles ):
        lastFilenameFound = thisFilename
        numFound += 1
    if numFound:
        if Globals.verbosityLevel > 2: print( "TheWordBibleFileCheck got", numFound, givenFolderName, lastFilenameFound )
        if numFound == 1 and autoLoad:
            twB = TheWordBible( givenFolderName, lastFilenameFound )
            twB.load() # Load and process the file
            return twB
        return numFound
    elif looksHopeful and Globals.verbosityLevel > 2: print( "    Looked hopeful but no actual files found" )

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if not os.access( tryFolderName, os.R_OK ): # The subfolder is not readable
            logging.warning( _("TheWordBibleFileCheck: '{}' subfolder is unreadable").format( tryFolderName ) )
            continue
        if Globals.verbosityLevel > 3: print( "    TheWordBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
        foundSubfolders, foundSubfiles = [], []
        for something in os.listdir( tryFolderName ):
            somepath = os.path.join( givenFolderName, thisFolderName, something )
            if os.path.isdir( somepath ): foundSubfolders.append( something )
            elif os.path.isfile( somepath ):
                somethingUpper = something.upper()
                somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
                #ignore = False
                #for ending in filenameEndingsToIgnore:
                    #if somethingUpper.endswith( ending): ignore=True; break
                #if ignore: continue
                #if not somethingUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
                if somethingUpperExt in filenameEndingsToAccept:
                    foundSubfiles.append( something )

        # See if there's an TW project here in this folder
        for thisFilename in sorted( foundSubfiles ):
            foundProjects.append( (tryFolderName, thisFilename,) )
            lastFilenameFound = thisFilename
            numFound += 1
    if numFound:
        if Globals.verbosityLevel > 2: print( "TheWordBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and autoLoad:
            if Globals.debugFlag: assert( len(foundProjects) == 1 )
            twB = TheWordBible( foundProjects[0][0], foundProjects[0][1] )
            twB.load() # Load and process the file
            return twB
        return numFound
# end of TheWordBibleFileCheck



def theWordGetBBBCV( lineNumber, volumeType='BOTH' ):
    """
    Given a line number (0... )
        return BBB, C, V 3-tuple.

    volumeType is 'OT', 'NT', or 'Both'.

    if lineNumber is beyond the verse lines, returns BBB='MDA' for metadata
    """
    assert( 0 <= lineNumber < 32000 )
    assert( volumeType in ('OT','NT','BOTH',) )

    if volumeType == 'OT':
        bookCount, books, totalLines, bookLines = theWordOTBookCount, theWordOTBooks, theWordOTTotalLines, theWordOTBookLines
    elif volumeType == 'NT':
        bookCount, books, totalLines, bookLines = theWordNTBookCount, theWordNTBooks, theWordNTTotalLines, theWordNTBookLines
    elif volumeType == 'BOTH':
        bookCount, books, totalLines, bookLines = theWordBookCount, theWordBooks, theWordTotalLines, theWordBookLines

    if lineNumber >= totalLines: return 'MDA', 0, lineNumber - totalLines

    # Find the book chapter and verse
    runningTotal = 0
    for BBB, lines in zip( books, bookLines ):
        if lineNumber < (runningTotal + lines): # we're in this book
            verseList = BOS.getNumVersesList( BBB )
            verseTotal = 0
            for j, verseCount in enumerate( verseList ):
                C = j + 1
                if lineNumber < (runningTotal + verseTotal + verseCount ):
                    return BBB, C, lineNumber - runningTotal - verseTotal + 1
                verseTotal += verseCount
            halt # programming error
        runningTotal += lines
# end of theWordGetBBBCV



def theWordFileCompare( filename1, filename2, folder1=None, folder2=None, printFlag=True, exitCount=10 ):
    """
    Compare the two files.
    """
    filepath1 = os.path.join( folder1, filename1 ) if folder1 else filename1
    filepath2 = os.path.join( folder2, filename2 ) if folder2 else filename2
    if Globals.verbosityLevel > 1:
        if filename1==filename2:
            print( "Comparing {} files in folders {} and {}...".format( repr(filename1), repr(folder1), repr(folder2) ) )
        else: print( "Comparing files {} and {}...".format( repr(filename1), repr(filename2) ) )

    # Do a preliminary check on the readability of our files
    if not os.access( filepath1, os.R_OK ):
        logging.error( "theWordFileCompare: File1 '{}' is unreadable".format( filepath1 ) )
        return None
    if not os.access( filepath2, os.R_OK ):
        logging.error( "theWordFileCompare: File2 '{}' is unreadable".format( filepath2 ) )
        return None

    # Read the files
    lineCount, lines1 = 0, []
    with open( filepath1, 'rt' ) as file1:
        for line in file1:
            lineCount += 1
            if lineCount==1 and line[0]==chr(65279): #U+FEFF
                if printFlag and Globals.verbosityLevel > 2:
                    print( "      theWordFileCompare: Detected UTF-16 Byte Order Marker in file1" )
                line = line[1:] # Remove the UTF-8 Byte Order Marker
            if line[-1]=='\n': line=line[:-1] # Removing trailing newline character
            #if not line: continue # Just discard blank lines
            lines1.append( line )
    lineCount, lines2 = 0, []
    with open( filepath2, 'rt' ) as file2:
        for line in file2:
            lineCount += 1
            if lineCount==1 and line[0]==chr(65279): #U+FEFF
                if printFlag and Globals.verbosityLevel > 2:
                    print( "      theWordFileCompare: Detected UTF-16 Byte Order Marker in file2" )
                line = line[1:] # Remove the UTF-8 Byte Order Marker
            if line[-1]=='\n': line=line[:-1] # Removing trailing newline character
            #if not line: continue # Just discard blank lines
            line = line.replace( "ʼ", "'" ) # Change back to a straight apostrophe for comparison
            lines2.append( line )

    len1, len2 = len(lines1), len(lines2 )
    equalFlag = True
    if len1 != len2:
        if printFlag: print( "Count of lines differ: file1={}, file2={}".format( len1, len2 ) )
        equalFlag = False

    testament = 'BOTH'
    if filename1.lower().endswith( '.nt' ): testament = 'NT'
    elif filename1.lower().endswith( '.ot' ): testament = 'OT'
    diffCount = 0
    for k in range( 0, min( len1, len2 ) ):
        if lines1[k] != lines2[k]:
            if printFlag:
                BBB, C, V = theWordGetBBBCV( k, testament )
                print( "  {} {}:{} {}:{} ({} chars)\n  {} {}:{} {}:{} ({} chars)" \
                        .format( BBB, C, V, k+1, repr(lines1[k]), len(lines1[k]), \
                                BBB, C, V, k+1, repr(lines2[k]), len(lines2[k]) ) )
            if printFlag and Globals.verbosityLevel > 2:
                for x in range( 0, min( len(lines1[k]), len(lines2[k]) ) ):
                    if lines1[k][x] != lines2[k][x]:
                        print( "      Differ at position {} '{}' vs '{}'".format( x+1, lines1[k][x], lines2[k][x] ) )
                        break
            equalFlag = False
            diffCount += 1
            if diffCount > exitCount:
                if printFlag and Globals.verbosityLevel > 1:
                    print( "theWordfileCompare: stopped comparing after {} mismatches".format( exitCount ) )
                break

    return equalFlag
# end of theWordFileCompare


# These next three functions are used both by theWord and MySword exports
theWordIgnoredIntroMarkers = oftenIgnoredIntroMarkers + (
    'imt1','imt2','imt3','is1','is2','is3',
    'ip','ipi','im','imi','ipq','imq','ir','iq1','iq2','iq3','ib','ili',
    'iot','io1','io2','io3','ir','iex','iqt','imte','ie','mte',)

def theWordHandleIntroduction( BBB, bookData, ourGlobals ):
    """
    Go through the book introduction (if any) and extract main titles for theWord export.

    Parameters are BBB (for error messages),
        the actual book data, and
        ourGlobals dictionary for persistent variables.

    Returns the information in a composed line string.
    """
    C = V = 0
    composedLine = ''
    while True:
        #print( "theWordHandleIntroduction", BBB, C, V )
        try: result = bookData.getCVRef( (BBB,'0',str(V),) ) # Currently this only gets one line
        except KeyError: break # Reached the end of the introduction
        verseData, context = result
        assert( len(verseData ) == 1 ) # in the introductory section
        marker, text = verseData[0].getMarker(), verseData[0].getFullText()
        if marker not in theWordIgnoredIntroMarkers:
            if marker=='mt1': composedLine += '<TS1>'+theWordAdjustLine(BBB,C,V,text)+'<Ts>'
            elif marker=='mt2': composedLine += '<TS2>'+theWordAdjustLine(BBB,C,V,text)+'<Ts>'
            elif marker=='mt3': composedLine += '<TS3>'+theWordAdjustLine(BBB,C,V,text)+'<Ts>'
            elif marker=='ms1': composedLine += '<TS2>'+theWordAdjustLine(BBB,C,V,text)+'<Ts>'
            elif marker=='ms2': composedLine += '<TS3>'+theWordAdjustLine(BBB,C,V,text)+'<Ts>'
            elif marker=='mr': composedLine += '<TS3>'+theWordAdjustLine(BBB,C,V,text)+'<Ts>'
            else:
                logging.warning( "theWordHandleIntroduction: doesn't handle {} '{}' yet".format( BBB, marker ) )
                if Globals.debugFlag and debuggingThisModule:
                    print( "theWordHandleIntroduction: doesn't handle {} '{}' yet".format( BBB, marker ) )
                    halt
                ourGlobals['unhandledMarkers'].add( marker + ' (in intro)' )
        V += 1 # Step to the next introductory section "verse"

    # Check what's left at the end
    if '\\' in composedLine:
        logging.warning( "theWordHandleIntroduction: Doesn't handle formatted line yet: {} '{}'".format( BBB, composedLine ) )
        if Globals.debugFlag and debuggingThisModule:
            print( "theWordHandleIntroduction: Doesn't handle formatted line yet: {} '{}'".format( BBB, composedLine ) )
            halt
    return composedLine
# end of theWordHandleIntroduction


def theWordAdjustLine( BBB, C, V, originalLine ):
    """
    Handle pseudo-USFM markers within the line (cross-references, footnotes, and character formatting).

    Parameters are the Scripture reference (for error messsages)
        and the line (string) containing the backslash codes.

    Returns a string with the backslash codes replaced by theWord formatting codes.
    """
    line = originalLine # Keep a copy of the original line for error messages

    if '\\x' in line: # Remove cross-references completely (why???)
        #line = line.replace('\\x ','<RX>').replace('\\x*','<Rx>')
        line = removeUSFMCharacterField( 'x', line, closed=True ).lstrip() # Remove superfluous spaces

    if '\\f' in line: # Handle footnotes
        for marker in ( 'fr', 'fm', ): # simply remove these whole field
            line = removeUSFMCharacterField( marker, line, closed=None )
        for marker in ( 'fq', 'fqa', 'fl', 'fk', ): # italicise these ones
            while '\\'+marker+' ' in line:
                #print( BBB, C, V, marker, line.count('\\'+marker+' '), line )
                #print( "was", "'"+line+"'" )
                ix = line.find( '\\'+marker+' ' )
                assert( ix != -1 )
                ixEnd = line.find( '\\', ix+len(marker)+2 )
                if ixEnd == -1: # no following marker so assume field stops at the end of the line
                    line = line.replace( '\\'+marker+' ', '<i>' ) + '</i>'
                elif line[ixEnd:].startswith( '\\'+marker+'*' ): # replace the end marker also
                    line = line.replace( '\\'+marker+' ', '<i>' ).replace( '\\'+marker+'*', '</i>' )
                else: # leave the next marker in place
                    line = line[:ixEnd].replace( '\\'+marker+' ', '<i>' ) + '</i>' + line[ixEnd:]
        for marker in ( 'ft', ): # simply remove these markers (but leave behind the text field)
            line = line.replace( '\\'+marker+' ', '' ).replace( '\\'+marker+'*', '' )
        #for caller in '+*abcdefghijklmnopqrstuvwxyz': line.replace('\\f '+caller+' ','<RF>') # Handle single-character callers
        line = re.sub( r'(\\f [a-z+*]{1,3} )', '<RF>', line ) # Handle one to three character callers
        line = line.replace('\\f ','<RF>').replace('\\f*','<Rf>') # Must be after the italicisation
        #if '\\f' in originalLine:
            #print( "o", originalLine )
            #print( "n", line )
            #halt

    if '\\' in line: # Handle character formatting fields
        line = removeUSFMCharacterField( 'fig', line, closed=True ) # Remove figures
        replacements = (
            ( ('add',), '<FI>','<Fi>' ),
            ( ('qt',), '<FO>','<Fo>' ),
            ( ('wj',), '<FR>','<Fr>' ),
            ( ('bdit',), '<b><i>','</i></b>' ),
            ( ('bd','em','k',), '<b>','</b>' ),
            ( ('it','rq','bk','dc','qs','sig','sls','tl',), '<i>','</i>' ),
            ( ('nd','sc',), '<font size=-1>','</font>' ),
            )
        line = replaceUSFMCharacterFields( replacements, line ) # This function also handles USFM 2.4 nested character markers
        if '\\nd' not in originalLine and '\\+nd' not in originalLine:
            line = line.replace('LORD', '<font size=-1>LORD</font>')
            #line = line.replace('\\nd ','<font size=-1>',).replace('\\nd*','</font>').replace('\\+nd ','<font size=-1>',).replace('\\+nd*','</font>')
        #else:
            #line = line.replace('LORD', '<font size=-1>LORD</font>')
        #line = line.replace('\\add ','<FI>').replace('\\add*','<Fi>').replace('\\+add ','<FI>').replace('\\+add*','<Fi>')
        #line = line.replace('\\qt ','<FO>').replace('\\qt*','<Fo>').replace('\\+qt ','<FO>').replace('\\+qt*','<Fo>')
        #line = line.replace('\\wj ','<FR>').replace('\\wj*','<Fr>').replace('\\+wj ','<FR>').replace('\\+wj*','<Fr>')

    #if '\\' in line: # Output simple HTML tags (with no semantic info)
        #line = line.replace('\\bdit ','<b><i>').replace('\\bdit*','</i></b>').replace('\\+bdit ','<b><i>').replace('\\+bdit*','</i></b>')
        #for marker in ( 'it', 'rq', 'bk', 'dc', 'qs', 'sig', 'sls', 'tl', ): # All these markers are just italicised
            #line = line.replace('\\'+marker+' ','<i>').replace('\\'+marker+'*','</i>').replace('\\+'+marker+' ','<i>').replace('\\+'+marker+'*','</i>')
        #for marker in ( 'bd', 'em', 'k', ): # All these markers are just bolded
            #line = line.replace('\\'+marker+' ','<b>').replace('\\'+marker+'*','</b>').replace('\\+'+marker+' ','<b>').replace('\\+'+marker+'*','</b>')
        #line = line.replace('\\sc ','<font size=-1>',).replace('\\sc*','</font>').replace('\\+sc ','<font size=-1>',).replace('\\+sc*','</font>')

    # Check what's left at the end
    if '\\' in line:
        logging.warning( "theWordAdjustLine: Doesn't handle formatted line yet: {} {}:{} '{}'".format( BBB, C, V, line ) )
        if Globals.debugFlag and debuggingThisModule:
            print( "theWordAdjustLine: Doesn't handle formatted line yet: {} {}:{} '{}'".format( BBB, C, V, line ) )
            halt
    return line
# end of theWordAdjustLine


def resetTheWordMargins( ourGlobals, setKey=None ):
    """
    Reset all of our persistent margin variables.

    If a key name is given, just set that one to True.
    """
    #nonlocal ourGlobals
    #was = ourGlobals['pi1']
    ourGlobals['pi1'] = ourGlobals['pi2'] = ourGlobals['pi3'] = ourGlobals['pi4'] = ourGlobals['pi5'] = ourGlobals['pi6'] = ourGlobals['pi7'] = False
    ourGlobals['title'] = False # not sure yet if we need this one
    if setKey: ourGlobals[setKey] = True
    #if was and not ourGlobals['pi1']:
        #print( "Went off at", BBB, C, V, marker, text )
        #if BBB=='MAT' and C==4 and V==17: halt
# end of resetTheWordMargins


def theWordComposeVerseLine( BBB, C, V, verseData, ourGlobals ):
    """
    Composes a single line representing a verse.

    Parameters are the Scripture reference (for error messages),
        the verseData (a list of InternalBibleEntries: pseudo-USFM markers and their contents),
        and a ourGlobals dictionary for holding persistent variables (between calls).

    This function handles the paragraph/new-line markers;
        theWordAdjustLine (above) is called to handle internal/character markers.

    Returns the composed line.
    """
    #print( "theWordComposeVerseLine( {} {}:{} {} {}".format( BBB, C, V, verseData, ourGlobals ) )
    composedLine = ourGlobals['line'] # We might already have some book headings to precede the text for this verse
    ourGlobals['line'] = '' # We've used them so we don't need them any more
    #marker = text = None

    vCount = 0
    lastMarker = None
    #if BBB=='MAT' and C==4 and 14<V<18: print( BBB, C, V, ourGlobals, verseData )
    for verseDataEntry in verseData:
        marker, text = verseDataEntry.getMarker(), verseDataEntry.getFullText()
        if marker in ('c','c#','cl','cp','rem',): lastMarker = marker; continue  # ignore all of these for this

        if marker == 'v': # handle versification differences here
            vCount += 1
            if vCount == 1: # Handle verse bridges
                if text != str(V):
                    composedLine += '<sup>('+text+')</sup> ' # Put the additional verse number into the text in parenthesis
            elif vCount > 1: # We have an additional verse number
                assert( text != str(V) )
                composedLine += ' <sup>('+text+')</sup>' # Put the additional verse number into the text in parenthesis
            lastMarker = marker
            continue

        #print( "theWordComposeVerseLine:", BBB, C, V, marker, text )
        if marker in theWordIgnoredIntroMarkers:
            logging.error( "theWordComposeVerseLine: Found unexpected {} introduction marker at {} {}:{} {}".format( marker, BBB, C, V, repr(text) ) )
            print( "theWordComposeVerseLine:", BBB, C, V, marker, text, verseData )
            if Globals.debugFlag and debuggingThisModule: assert( marker not in theWordIgnoredIntroMarkers ) # these markers shouldn't occur in verses

        if marker == 's1':
            if ourGlobals['lastLine'] is not None and not composedLine: # i.e., don't do it for the very first line
                ourGlobals['lastLine'] = ourGlobals['lastLine'].rstrip() + '<CM>' # append the new paragraph marker to the previous line
            composedLine += '<TS1>'+theWordAdjustLine(BBB,C,V,text)+'<Ts>'
        elif marker == 's2': composedLine += '<TS2>'+theWordAdjustLine(BBB,C,V,text)+'<Ts>'
        elif marker in ( 's3', 'sr', 'd', ): composedLine += '<TS3>'+theWordAdjustLine(BBB,C,V,text)+'<Ts>'
        elif marker in ( 'qa', 'r', ):
            if marker=='r' and text and text[0]!='(' and text[-1]!=')': # Put parenthesis around this if not already there
                text = '(' + text + ')'
            composedLine += '<TS3><i>'+theWordAdjustLine(BBB,C,V,text)+'</i><Ts>'
        elif marker in ( 'm', ):
            assert( not text )
            if ourGlobals['lastLine'] is not None and not composedLine: # i.e., don't do it for the very first line
                ourGlobals['lastLine'] = ourGlobals['lastLine'].rstrip() + '<CL>' # append the new paragraph marker to the previous line
            #if text:
                #print( 'm', repr(text), verseData )
                #composedLine += '<CL>'+theWordAdjustLine(BBB,C,V,text)
                #if ourGlobals['pi1'] or ourGlobals['pi2'] or ourGlobals['pi3'] or ourGlobals['pi4'] or ourGlobals['pi5'] or ourGlobals['pi6'] or ourGlobals['pi7']:
                    #composedLine += '<CL>'
                #else: composedLine += '<CM>'
            #else: # there is text
                #composedLine += '<CL>'+theWordAdjustLine(BBB,C,V,text)
        elif marker in ( 'p', 'b', ):
            #print( marker, text )
            assert( not text )
            if ourGlobals['lastLine'] is not None and not composedLine: # i.e., don't do it for the very first line
                ourGlobals['lastLine'] = ourGlobals['lastLine'].rstrip() + '<CM>' # append the new paragraph marker to the previous line
            #else: composedLine += '<CM>'
            #composedLine += theWordAdjustLine(BBB,C,V,text)
            resetTheWordMargins( ourGlobals )
        elif marker in ( 'pi1', ):
            assert( not text )
            resetTheWordMargins( ourGlobals, 'pi1' ); composedLine += '<CM><PI>'+theWordAdjustLine(BBB,C,V,text)
        elif marker in ( 'pi2', ):
            assert( not text )
            resetTheWordMargins( ourGlobals, 'pi2' ); composedLine += '<CM><PI2>'+theWordAdjustLine(BBB,C,V,text)
        elif marker in ( 'pi3', 'pmc', ):
            assert( not text )
            resetTheWordMargins( ourGlobals, 'pi3' ); composedLine += '<CM><PI3>'+theWordAdjustLine(BBB,C,V,text)
        elif marker in ( 'pi4', ):
            assert( not text )
            resetTheWordMargins( ourGlobals, 'pi4' ); composedLine += '<CM><PI4>'+theWordAdjustLine(BBB,C,V,text)
        elif marker in ( 'pc', ):
            assert( not text )
            resetTheWordMargins( ourGlobals, 'pi5' ); composedLine += '<CM><PI5>'+theWordAdjustLine(BBB,C,V,text)
        elif marker in ( 'pr', 'pmr', 'cls', ):
            assert( not text )
            resetTheWordMargins( ourGlobals, 'pi6' ); composedLine += '<CM><PI6>'+theWordAdjustLine(BBB,C,V,text) # Originally right-justified
        elif marker in ( 'b', 'mi', 'pm', 'pmo', ):
            assert( not text )
            resetTheWordMargins( ourGlobals, 'pi7' ); composedLine += '<CM><PI7>'+theWordAdjustLine(BBB,C,V,text)
        elif marker in ( 'q1', 'qm1', ):
            assert( not text )
            if ourGlobals['lastLine'] is not None and not composedLine: # i.e., don't do it for the very first line
                ourGlobals['lastLine'] += '<CI>' # append the new quotation paragraph marker to the previous line
            else: composedLine += '<CI>'
            if not ourGlobals['pi1']: composedLine += '<PI>'
            resetTheWordMargins( ourGlobals, 'pi1' )
            #composedLine += theWordAdjustLine(BBB,C,V,text)
        elif marker in ( 'q2', 'qm2', ):
            assert( not text )
            if ourGlobals['lastLine'] is not None and not composedLine: # i.e., don't do it for the very first line
                ourGlobals['lastLine'] += '<CI>' # append the new quotation paragraph marker to the previous line
            else: composedLine += '<CI>'
            if not ourGlobals['pi2']: composedLine += '<PI2>'
            resetTheWordMargins( ourGlobals, 'pi2' )
            #composedLine += '<CI><PI2>'+theWordAdjustLine(BBB,C,V,text)
        elif marker in ( 'q3', 'qm3', ):
            assert( not text )
            if ourGlobals['lastLine'] is not None and not composedLine: # i.e., don't do it for the very first line
                ourGlobals['lastLine'] += '<CI>' # append the new quotation paragraph marker to the previous line
            else: composedLine += '<CI>'
            if not ourGlobals['pi3']: composedLine += '<PI3>'
            resetTheWordMargins( ourGlobals, 'pi3' )
            #composedLine += '<CI><PI3>'+theWordAdjustLine(BBB,C,V,text)
        elif marker in ( 'q4', 'qm4', ):
            assert( not text )
            if ourGlobals['lastLine'] is not None and not composedLine: # i.e., don't do it for the very first line
                ourGlobals['lastLine'] += '<CI>' # append the new quotation paragraph marker to the previous line
            else: composedLine += '<CI>'
            if not ourGlobals['pi4']: composedLine += '<PI4>'
            resetTheWordMargins( ourGlobals, 'pi4' )
            #composedLine += '<CI><PI4>'+theWordAdjustLine(BBB,C,V,text)
        elif marker == 'li1': resetTheWordMargins( ourGlobals, 'pi1' ); composedLine += '<PI>• '+theWordAdjustLine(BBB,C,V,text)
        elif marker == 'li2': resetTheWordMargins( ourGlobals, 'pi2' ); composedLine += '<PI2>• '+theWordAdjustLine(BBB,C,V,text)
        elif marker == 'li3': resetTheWordMargins( ourGlobals, 'pi3' ); composedLine += '<PI3>• '+theWordAdjustLine(BBB,C,V,text)
        elif marker == 'li4': resetTheWordMargins( ourGlobals, 'pi4' ); composedLine += '<PI4>• '+theWordAdjustLine(BBB,C,V,text)
        elif marker in ( 'cd', 'sp', ): composedLine += '<i>'+theWordAdjustLine(BBB,C,V,text)+'</i>'
        elif marker in ( 'v~', 'p~', ):
            #print( lastMarker )
            if lastMarker == 'p': composedLine += '<CM>' # We had a continuation paragraph
            elif lastMarker == 'm': composedLine += '<CL>' # We had a continuation paragraph
            elif lastMarker in Globals.USFMParagraphMarkers: pass # Did we need to do anything here???
            elif lastMarker != 'v':
                print( BBB, C, V, marker, lastMarker, verseData )
                composedLine += theWordAdjustLine(BBB,C,V, text )
                if Globals.debugFlag and debuggingThisModule: halt # This should never happen -- probably a b marker with text
            #if ourGlobals['pi1']: composedLine += '<PI>'
            #elif ourGlobals['pi2']: composedLine += '<PI2>'
            #elif ourGlobals['pi3']: composedLine += '<PI3>'
            #elif ourGlobals['pi4']: composedLine += '<PI4>'
            #elif ourGlobals['pi5']: composedLine += '<PI5>'
            #elif ourGlobals['pi6']: composedLine += '<PI6>'
            #elif ourGlobals['pi7']: composedLine += '<PI7>'
            composedLine += theWordAdjustLine(BBB,C,V, text )
        else:
            logging.warning( "theWordComposeVerseLine: doesn't handle '{}' yet".format( marker ) )
            if Globals.debugFlag and debuggingThisModule:
                print( "theWordComposeVerseLine: doesn't handle '{}' yet".format( marker ) )
                halt
            ourGlobals['unhandledMarkers'].add( marker )
        lastMarker = marker

    # Final clean-up
    composedLine = composedLine.replace( '<CM><CI>', '<CM>' ) # paragraph mark not needed when following a title close marker
    while '  ' in composedLine: # remove double spaces
        composedLine = composedLine.replace( '  ', ' ' )

    # Check what's left at the end
    if '\\' in composedLine:
        logging.warning( "theWordComposeVerseLine: Doesn't handle formatted line yet: {} {}:{} '{}'".format( BBB, C, V, composedLine ) )
        if Globals.debugFlag and debuggingThisModule:
            print( "theWordComposeVerseLine: Doesn't handle formatted line yet: {} {}:{} '{}'".format( BBB, C, V, composedLine ) )
            halt
    return composedLine.rstrip()
# end of theWordComposeVerseLine




def handleLine( myName, BBB, C, V, originalLine, bookObject, myGlobals ):
    """
    Adjusts the formatting of the line for Bible reference BBB C:V
        and then writes it to the bookObject.

    Try to convert display formatting to semantic formatting as much as possible

    myGlobals dict contains flags.

    Appends pseudo-USFM results to the supplied bookObject.

    NOTE: There are no checks in here yet to discover nested character-formatting markers.  :-(
    """
    if Globals.debugFlag:
        if debuggingThisModule:
            print( "TheWordBible.handleLine( {} {} {}:{} {} ... {}".format( myName, BBB, C, V, repr(originalLine), myGlobals ) )
        assert( '\n' not in originalLine and '\r' not in originalLine )
    line = originalLine

    writtenV = False
    if V==1: appendedCFlag = False
    if C!=1 and V==1: bookObject.appendLine( 'c', str(C) ); appendedCFlag = True

    if line is None: # We don't have an entry for this C:V
        return

    if line.startswith( '<CM>' ):
        print( "Why does theWord line start with <CM>?", myName, BBB, C, V, repr(originalLine) )

    # Fix apparent encoding errors in particular modules
    line = line.replace( ' >', '>' ) # fpr1933
    if line.endswith( '<CM' ): line += '>' # asv.ont
    if line.startswith( '>  ' ): line = line[3:] # pinyin.ont
    line = line.replace( '<TS><Ts>', '' ) # Fixes a module bug (has an empty field)
    line = line.replace( '<PF0><PF0>', '<PF0>' ) # 20cNT
    line = line.replace( '<PF0><PF1>', '<PF1>' ) # 20cNT
    line = line.replace( '<CM><CI>', '<CI>' ) # 20cNT
    line = line.replace( '<CI><CI>', '<CI>' ) # Tanakh1917.ot
    line = line.replace( '<CM><TS', '<TS' ) # 20cNT, gertextbibel
    line = line.replace( '(<12>) ', '' ).replace( '(<13>) ', '' ) # afr1953
    match = re.search( '<CT>(.+?)<CG> ', line ) # Lots found in alb
    if match:
        logging.warning( "Removed {} {} {}:{} unknown field {} from {}" \
            .format( myName, BBB, C, V, repr(line[match.start():match.end()]), repr(originalLine) ) )
        line = line[:match.start()] + line[match.end():]
    line = line.replace( ' <CLX>', '' ) # Undocumented what this means
    line = line.replace( '</<sup>>', '</sup>' ) # aleppo
    if line.endswith( '<CI><PI2>' ): line = line[:-5] # remove <PI2> from Tanakh1917
    line = line.replace( '<26-Ezekiel.21:3>', '' ) # Tanakh1917
    #if '\xa0' in line: print( myName, BBB, C, V, repr(originalLine) ); halt
    line = line.replace( '\xa0', ' ' ) # NBSpace? Not sure what this is (in aleppo and arm1967 and others?)
    if line.endswith( ' <CM>\t' ): line = line.replace( ' <CM>\t', '<CM>' ) # asv
    line = re.sub( '<V (\d{1,3}):(\d{1,3})>', '', line ) # cpdv for some verses
    line = re.sub( '<V P:(\d{1,2})>', '', line ) # cpdv for some prologue verses
    line = re.sub( '<RX (\d{1,2})\.(\d{1,3})\.(\d{1,3})>', '', line ) # dutsv
    #line = re.sub( '<RX (\d{1,2})\.(\d{1,3})\.(\d{1,2}) >', '', line ) # fpr1933
    line = re.sub( '<RX (\d{1,2})\.(\d{1,3})\.(\d{1,3})[+-\.](\d{1,3})>', '', line ) # dutsv, fpr1933
    #line = line.replace( '<BOOK THE FIRST> ', '' ) # ebr
    line = line.replace( ' /a>', '' ) # jfa-rc(pt)
    line = line.replace( '?>> A', '? A' ).replace( 'viu>.', 'viu.' ) # romorthodox
    line = re.sub( '<V1{>(.*?)<V1}>', r'\1', line ) # tr.nt
    line = re.sub( '<V2(.+?)>', '', line ) # remove variant 2 from tr.nt
    line = line.replace( '<CM> <CM> <TS>', '<TS>' ).replace( '<CM> <CM>', '<CM>' ) # web

    # Not sure what <A represents, but it's often at the beginning of a line and messes up other tests
    #   so lets remove them here
    line = re.sub( '<AX (.+?)>', '', line ) # fpr1933
    line = re.sub( '<A(\d{1,3}):(\d{1,2})>', '', line )
    line = re.sub( '<A (\d{1,3})\.(\d{1,2})>', '', line )
    #if '<A' in line:
        #print( "line3", repr(originalLine), '\n', repr(line) )
        #if Globals.debugFlag: halt
    line = re.sub( '<22-Song of Songs\.(\d{1,2})\.(\d{1,2})>', '', line ) # Tanakh1917
    line = line.replace( '<z1>', '' ).replace( '<z2>', '' ) # footnote referent text in leb
    line = re.sub( '<AF(.)(.*?)>', '', line ) # sblgnt.nt seems to have alternatives immediately before the word
    line = re.sub( '<AU(.)>', '', line ) # sblgnt.nt seems to have this immediately after the word
    line = re.sub( '<a href=(.+?)>(.+?)</a>', '', line ) # slt.ont has these html links
    line = re.sub( '<sync type="(.+?)" value="(.+?)" />', '', line ) # spasev.ont has these links


    # Adjust paragraph formatting at the beginning of lines
    # Don't need to include a \p before a \q1 or whatever
    if line.startswith( '<PF0>' ):
        line = line.replace( '<PF0>', '\\q1 ', 1 )
        myGlobals['haveParagraph'] = False
    elif line.startswith( '<PF1><PI1>' ):
        line = line.replace( '<PF1><PI1>', '\\q1 ', 1 )
        myGlobals['haveParagraph'] = False
    elif line.startswith( '<PF1>' ):
        line = line.replace( '<PF1>', '\\q1 ', 1 )
        myGlobals['haveParagraph'] = False
    elif line.startswith( '<PI>' ):
        line = line.replace( '<PI>', '\\q1 ', 1 )
        myGlobals['haveParagraph'] = False
    elif line.startswith( '<PI1>' ):
        line = line.replace( '<PI1>', '\\q1 ', 1 )
        myGlobals['haveParagraph'] = False
    elif line.startswith( '<PI2>' ):
        line = line.replace( '<PI2>', '\\q2 ', 1 )
        myGlobals['haveParagraph'] = False
    elif line.startswith( '<PI3>' ):
        line = line.replace( '<PI3>', '\\q3 ', 1 )
        myGlobals['haveParagraph'] = False
    elif line.startswith( '<CI>' ):
        myGlobals['haveParagraph'] = False
        if line.startswith( '<CI><PI2>' ):
            line = line.replace( '<CI><PI2>', '<CI><PI2>\\NL*', 1 ) # This will cause the first q to be followed by a v
    elif line.startswith( '<CL>' ):
        myGlobals['haveParagraph'] = False

    # Handle some special cases
    line = line.replace('<TS3><i>(','\\NL*\\r (').replace(')</i>',')') # The TS3 ending will be covered below

    # Adjust line formatting
    if C==1 and V==1 and originalLine and originalLine[0]=='<': # These are right at the beginning of the book
        line = line.replace('<TS>','\\NL*\\mt1 ').replace('<Ts>','\\NL*')
        line = line.replace('<TS1>','\\NL*\\mt1 ').replace('<Ts1>','\\NL*') # Start marker and then a newline at end
        line = line.replace('<TS2>','\\NL*\\mt2 ').replace('<Ts2>','\\NL*')
        line = line.replace('<TS3>','\\NL*\\mt3 ').replace('<Ts3>','\\NL*')
    else: # we'll assume that they're section headings
        if line.startswith( '<TS' ): myGlobals['haveParagraph'] = False # Don't need a paragraph marker before a section heading
        line = line.replace('<TS>','\\NL*\\s1 ').replace('<Ts>','\\NL*')
        line = line.replace('<TS1>','\\NL*\\s1 ').replace('<Ts1>','\\NL*') # Start marker and then a newline at end
        line = line.replace('<TS2>','\\NL*\\s2 ').replace('<Ts2>','\\NL*')
        line = line.replace('<TS3>','\\NL*\\s3 ').replace('<Ts3>','\\NL*')
    # Some (poor) modules end even the numbered TS fields with just <Ts>!!!

    # Adjust character formatting with USFM equivalents
    line = line.replace('<FI>','\\add ').replace('<Fi>','\\add*')
    line = line.replace('<FO>','\\qt ').replace('<Fo>','\\qt*')
    line = line.replace('<CI><FR><PF1><PI1>','\\NL*\\q1 \\wj ') # in 20cNT
    line = line.replace('<CI><FR><PF1>','\\NL*\\p \\wj ') # in 20cNT
    line = line.replace('<FR>','\\wj ').replace('<Fr>','\\wj*')
    line = line.replace('<FU>','\\ul ').replace('<Fu>','\\ul*') # Not USFM
    line = line.replace('<RF>','\\f \\ft ').replace('<Rf>','\\f*')
    line = line.replace('<RX>','\\x ').replace('<Rx>','\\x*')

    #Now the more complex ones that need regexs
    #line = line.replace('<RF q=*>','\\f * \\ft ').replace('<Rf>','\\f*')
    #if '<RF' in line:
        #print( "line1", repr(originalLine), '\n', repr(line) )
    line = re.sub( '<RF q=(.)>', r'\\f \1 \\ft ', line )
        #print( "line2", repr(originalLine), '\n', repr(line) )
    line = re.sub( '<WH(\d{1,4})>', '', line )
    line = line.replace( '<wh>','' )
    if '<WH' in line or '<wh' in line:
        print( "line4", repr(originalLine), '\n', repr(line) )
        #halt
    line = re.sub( '<l=(.+?)>', '', line )
    if '<l=' in line:
        print( "line5", repr(originalLine), '\n', repr(line) )
        #halt

    # Simple HTML tags (with no semantic info)
    line = line.replace('<b>','\\bd ').replace('</b>','\\bd*')
    line = line.replace('<i>','\\it ').replace('</i>','\\it*')
    line = line.replace('<u>','\\ul ').replace('</u>','\\ul*') # Not USFM
    line = line.replace( ' <BR> ', '\\NL*\\m ' ).replace( '<BR> ', '\\NL*\\m ' ).replace( '<BR>', '\\NL*\\m ' )
    line = line.replace( ' <br> ', '\\NL*\\m ' ).replace( '<br> ', '\\NL*\\m ' ).replace( '<br>', '\\NL*\\m ' )
    line = line.replace('<sup>','\\ord ').replace('</sup>','\\ord*') # Not proper USFM meaning
    line = re.sub('<font size=-1>(.+?)</font>', r'\\sc \1\\sc*', line ) # This causes nested markers in aleppo
    line = re.sub('<font size=\+1>(.+?)</font>', r'\\em \1\\em*', line )
    line = re.sub( '<font color=(.+?)>(.+?)</font>', r'\2', line )
    line = re.sub( '<font color=(.+?)>', '', line ).replace( '</font>','' ) # asv has <font color="850000"> with the closing on the next line
    line = re.sub( '<HEB>(.+?)<heb>', r'\\qac \1\\qac*', line ) # acrostic letter in asv
    line = re.sub( '<HEB>(.+?)<Heb>', r'\\nd \1\\nd*', line ) # divine name in rnkjv

    # Handle the paragraph at the end of the previous line
    if myGlobals['haveParagraph']: # from the end of the previous line
        bookObject.appendLine( 'p', '' )
        myGlobals['haveParagraph'] = False

    # Adjust paragraph formatting at the end of lines
    line = line.replace( '<CM><CM>', '\\NL*\\b<CM>' ) # 20cNT
    assert( not myGlobals['haveParagraph'] )
    if line.endswith( '<CM>' ): # Means start a new paragraph after this line
        line = line[:-4] # Remove the marker
        myGlobals['haveParagraph'] = 'CM'
    elif line.endswith( '<CI>' ): # Means start a new paragraph (without a space before it) after this line
        line = line[:-4] # Remove the marker
        myGlobals['haveParagraph'] = 'CI'
    elif line.endswith( '<CL>' ): # Means start on a new line
        line = line[:-4] # Remove the marker
        myGlobals['haveParagraph'] = 'CL'

    # Paragraph markers (not at the end of the line)
    #line = re.sub('<CI><PI(\d)>',r'\\NL*\\q\1 ',line).replace('<Ci>','')
    #line = re.sub('<CI><PF(\d)>',r'\\NL*\\q\1 ',line)
    line = line.replace( '<CI><PF0>','\\NL*\\p ' )
    line = line.replace( '<CI><PF1><PI1>','\\NL*\\q1 ' )
    line = line.replace( '<CI><PF1>','\\NL*\\p ' )
    line = line.replace( '<CI><PF2><PI2>', '\\NL*\\q2 ' )
    line = line.replace( '<CI><PF3><PI3>', '\\NL*\\q3 ' )
    line = line.replace( '<CI><PI>','\\NL*\\q1 ' )
    line = line.replace( '<CI><PI0>','\\NL*\\p ' )
    line = line.replace( '<CI><PI1>','\\NL*\\q1 ' )
    line = line.replace( '<CI><PI2>','\\NL*\\q2 ' ).replace('<Ci>','')
    line = line.replace( '<CI><PI3>','\\NL*\\q3 ' )
    line = line.replace( '<CI><PI4>','\\NL*\\q4 ' )
    #line = line.replace( '<CI><PI5>','\\NL*\\q4 ' )
    line = line.replace( '<CL><PI2>','\\NL*\\q2 ' )
    line = line.replace( '<CL>','\\NL*\\m ' )
    line = line.replace( '<CM><PI>','\\NL*\\q1 ' )
    line = line.replace( '<CM><PI5>','\\NL*\\q4 ' )
    line = line.replace( '<CM><PI6>','\\NL*\\q4 ' )
    line = line.replace( '<CM><PF1><PI1>', '\\NL*\\q1 ' )
    line = line.replace( '<CM><PF2><PI2>', '\\NL*\\q2 ' )
    line = line.replace( '<CM><PF3><PI3>', '\\NL*\\q3 ' )
    #line = line.replace( '<CM><PF4><PI4>', '\\NL*\\q4 ' )
    line = line.replace( '<CM><PF0>', '\\NL*\\m ' )
    line = line.replace( '<CM>', '\\NL*\\p ' )
    line = line.replace( '<PF0>','\\NL*\\p ')
    line = line.replace( '<PF1><PI1>','\\NL*\\q1 ' )
    line = line.replace( '<PI2>', '\\NL*\\q2 ' )

    line = line.replace( '<K>','').replace('<k>','')
    line = line.replace( '<R>','').replace('<r>','')
    line = line.replace( '<sub>','').replace('</sub>','')

    if myName == 'ebr': line = line.replace( '<', '\\em ' ).replace( '>', '\\em*' )

    # Check what's left at the end
    if ('<' in line or '>' in line) and myName not in ('ckjv-sc','ckjv-tc',):
        # NOTE: some modules can use these as speech marks so they might be part of the text!
        if '<WT' not in line and '<WG' not in line and '<WH' not in line:
            # Don't yet handle lines like this: βιβλος<WG976><WTN-NSF> γενεσεως<WG1078><WTN-GSF> ιησου<WG2424><WTN-GSM> χριστου<WG5547><WTN-GSM> υιου<WG5207><WTN-GSM> δαυιδ<WG1138><WTN-PRI> υιου<WG5207><WTN-GSM> αβρααμ<WG11><WTN-PRI>
            logging.error( "{} original line: {}".format( myName, repr(originalLine) ) )
            logging.error( "TheWordBible.load: Doesn't handle {} {}:{} formatted line yet: {}".format( BBB, C, V, repr(line) ) )
            if 1: # Unhandled stuff -- not done properly yet...............................................
                line = re.sub( '<(.+?)>', '', line ) # Remove all remaining sets of angle brackets
            if Globals.debugFlag: halt


    line = line.replace( '\\NL*\\NL*', '\\NL*' ) # Don't need double-ups
    if line.startswith( '\\NL*' ): line = line[4:] # Don't need nl at start of line
    if line.endswith( '\\p \\NL*'): line = line[:-5] # Don't need nl and then space at end of line
    if line.endswith( '\\q1 \\NL*'): line = line[:-5] # Don't need nl and then space at end of line
    if line.endswith( '\\q2 \\NL*'): line = line[:-5] # Don't need nl and then space at end of line
    if line.endswith( '\\q3 \\NL*'): line = line[:-5] # Don't need nl and then space at end of line
    if line.endswith( '\\q4 \\NL*'): line = line[:-5] # Don't need nl and then space at end of line
    if line.endswith( '\\NL*' ): line = line[:-4] # Don't need nl at end of line
    if '\\NL*' in line: # We need to break the original line into different USFM markers
        #print( "\nMessing with segments: {} {}:{} '{}'".format( BBB, C, V, line ) )
        segments = line.split( '\\NL*' )
        assert( len(segments) >= 2 )
        #print( " segments (split by backslash):", segments )
        leftovers = ''
        for segment in segments:
            if segment and segment[0] == '\\':
                bits = segment.split( None, 1 )
                #print( " bits", bits )
                marker = bits[0][1:]
                if len(bits) == 1:
                    #if bits[0] in ('\\p','\\b'):
                    if Globals.USFMMarkers.isNewlineMarker( marker ):
                        if C==1 and V==1 and not appendedCFlag: bookObject.appendLine( 'c', str(C) ); appendedCFlag = True
                        bookObject.appendLine( marker, '' )
                    else:
                        logging.error( "It seems that we had a blank '{}' field in '{}'".format( bits[0], originalLine ) )
                        #halt
                else:
                    assert( len(bits) == 2 )
                    if Globals.debugFlag and debuggingThisModule:
                        print( "\n{} {}:{} '{}'".format( BBB, C, V, originalLine ) )
                        print( "line", repr(line) )
                        print( "seg", repr(segment) )
                        print( "segments:", segments )
                        print( "bits", bits )
                        print( "marker", marker )
                        print( "leftovers", repr(leftovers) )
                        assert( marker in ('mt1','mt2','mt3', 's1','s2','s3', 'q1','q2','q3', 'r') )
                    if Globals.USFMMarkers.isNewlineMarker( marker ):
                        bookObject.appendLine( marker, bits[1] )
                    elif not writtenV:
                        bookObject.appendLine( 'v', '{} {}'.format( V, segment ) )
                        writtenV = True
                    else: leftovers += segment
            else: # What is segment is blank (\\NL* at end of line)???
                if C==1 and V==1 and not appendedCFlag: bookObject.appendLine( 'c', str(C) ); appendedCFlag = True
                if not writtenV:
                    bookObject.appendLine( 'v', '{} {}'.format( V, leftovers+segment ) )
                    writtenV = True
                else:
                    bookObject.appendLine( 'v~', leftovers+segment )
                leftovers = ''
                #if myGlobals['haveParagraph']:
                    #bookObject.appendLine( 'p', '' )
                    #myGlobals['haveParagraph'] = False
        if leftovers: logging.critical( "Had leftovers {}".format( repr(leftovers) ) )
        if Globals.debugFlag: assert( not leftovers )
        #halt
    else: # no newlines in the middle
        if C==1 and V==1 and not appendedCFlag: bookObject.appendLine( 'c', str(C) ); appendedCFlag = True
        bookObject.appendLine( 'v', '{} {}'.format( V, line ) )
        #if myGlobals['haveParagraph']:
            #bookObject.appendLine( 'p', '' )
            #myGlobals['haveParagraph'] = False
# end of TheWordBible.handleLine




from Bible import Bible, BibleBook
class TheWordBible( Bible ):
    """
    Class for reading, validating, and converting TheWordBible files.
    """
    def __init__( self, sourceFolder, givenFilename, encoding='utf-8' ):
        """
        Constructor: just sets up the Bible object.
        """
         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = 'theWord Bible object'
        self.objectTypeString = 'theWord'

        # Now we can set our object variables
        self.sourceFolder, self.sourceFilename, self.encoding = sourceFolder, givenFilename, encoding
        self.sourceFilepath =  os.path.join( self.sourceFolder, self.sourceFilename )

        # Do a preliminary check on the readability of our file
        if not os.access( self.sourceFilepath, os.R_OK ):
            logging.critical( _("TheWordBible: File '{}' is unreadable").format( self.sourceFilepath ) )

        filenameBits = os.path.splitext( self.sourceFilename )
        self.name = filenameBits[0]
        self.fileExtension = filenameBits[1]

        if self.fileExtension.upper().endswith('X'):
            logging.warning( _("TheWordBible: File '{}' is encrypted").format( self.sourceFilepath ) )
    # end of TheWordBible.__init__


    def load( self ):
        """
        Load a single source file and load book elements.
        """
        if Globals.verbosityLevel > 2: print( _("Loading {}...").format( self.sourceFilepath ) )

        fileExtensionUpper = self.fileExtension.upper()
        assert( fileExtensionUpper in filenameEndingsToAccept )
        if fileExtensionUpper.endswith('X'):
            logging.error( _("TheWordBible: File '{}' is encrypted").format( self.sourceFilepath ) )
            return

        if fileExtensionUpper in ('.ONT','.ONTX',):
            testament, BBB = 'BOTH', 'GEN'
            booksExpected, textLineCountExpected = theWordBookCount, theWordTotalLines
        elif fileExtensionUpper in ('.OT','.OTX',):
            testament, BBB = 'OT', 'GEN'
            booksExpected, textLineCountExpected = theWordOTBookCount, theWordOTTotalLines
        elif fileExtensionUpper in ('.NT','.NTX',):
            testament, BBB = 'NT', 'MAT'
            booksExpected, textLineCountExpected = theWordNTBookCount, theWordOTTotalLines

        # Create the first book
        thisBook = BibleBook( self.name, BBB )
        thisBook.objectNameString = "theWord Bible Book object"
        thisBook.objectTypeString = "theWord"

        verseList = BOS.getNumVersesList( BBB )
        numC, numV = len(verseList), verseList[0]
        C = V = 1

        lastLine, lineCount, bookCount = '', 0, 0
        ourGlobals = {}
        continued = ourGlobals['haveParagraph'] = False
        encodings = ['utf-8', 'ISO-8859-1', 'ISO-8859-15']
        encodings.remove( self.encoding ) # Remove the given encoding if included
        if self.encoding: encodings.insert( 0, self.encoding ) # Put the given encoding back in in the first position
        for encoding in encodings: # Start by trying the given encoding
            try:
                with open( self.sourceFilepath, 'rt', encoding=encoding ) as myFile: # Automatically closes the file when done
                    for sourceLine in myFile:
                        originalLine = sourceLine
                        lineCount += 1
                        if lineCount==1 and self.encoding.lower()=='utf-8' and originalLine[0]==chr(65279): #U+FEFF
                            logging.info( "      TheWordBible.load: Detected UTF-16 Byte Order Marker" )
                            originalLine = originalLine[1:] # Remove the UTF-8 Byte Order Marker
                        if originalLine[-1]=='\n': originalLine=originalLine[:-1] # Removing trailing newline character
                        line = originalLine
                        #lastLine = line

                        if lineCount <= textLineCountExpected: # assume it's verse text
                            #print ( lineCount, BBB, C, V, 'TW file line is "' + line + '"' )
                            if not line: logging.warning( "TheWordBible.load: Found blank verse line at {} {} {}:{}".format( lineCount, BBB, C, V ) )

                            handleLine( self.name, BBB, C, V, line, thisBook, ourGlobals )
                            V += 1
                            if V > numV:
                                C += 1
                                if C > numC: # Save this book now
                                    if Globals.verbosityLevel > 3: print( "Saving", BBB, bookCount+1 )
                                    self.saveBook( thisBook )
                                    bookCount += 1
                                    if bookCount >= booksExpected: break
                                    BBB = BOS.getNextBookCode( BBB )
                                    # Create the next book
                                    thisBook = BibleBook( self.name, BBB )
                                    thisBook.objectNameString = "theWord Bible Book object"
                                    thisBook.objectTypeString = "theWord"

                                    verseList = BOS.getNumVersesList( BBB )
                                    numC, numV = len(verseList), verseList[0]
                                    C = V = 1
                                    # Don't append c 1 yet, because there might be a book heading to precede it
                                else: # next chapter only
                                    #thisBook.appendLine( 'c', str(C) )
                                    numV = verseList[C-1]
                                    V = 1
                                #thisBook.appendLine( 'cc', str(C) ) # All chapter numbers except the first

                            #if ourGlobals['haveParagraph']:
                                #thisBook.appendLine( 'p', '' )
                                #ourGlobals['haveParagraph'] = False

                        else: # Should be module info at end of file (after all of the verse lines)
                            #print ( lineCount, 'TW file line is "' + line + '"' )
                            if not line: continue # Just discard additional blank lines
                            if line[0] == '#': continue # Just discard comment lines
                            if not continued:
                                if '=' not in line:
                                    logging.warning( "Missing equals sign from info line (ignored): {} '{}'".format( lineCount, line ) )
                                else: # Seems like a field=something type line
                                    bits = line.split( '=', 1 )
                                    assert( len(bits) == 2 )
                                    fieldName = bits[0]
                                    fieldContents = bits[1]
                                    if line.endswith( '\\' ): continued = True
                                    else: self.settingsDict[fieldName] = fieldContents
                            else: # continued
                                fieldContents += line
                                if not line.endswith( '\\' ):
                                    self.settingsDict[fieldName] = fieldContents
                                    continued = False
                        #if lineCount > 3:
                            #self.saveBook( thisBook )
                            #break

                if lineCount < textLineCountExpected:
                    logging.error( _("TheWord Bible module file seems too short: {}").format( self.sourceFilename ) )
                self.encoding = encoding
                break; # Get out of decoding loop because we were successful
            except UnicodeDecodeError:
                logging.critical( _("TheWord Bible module file fails with encoding: {} {}").format( self.sourceFilename, self.encoding ) )
        #print( self.settingsDict ); halt
        if 'description' in self.settingsDict and len(self.settingsDict['description'])<40: self.name = self.settingsDict['description']
        if 'short.title' in self.settingsDict: self.shortName = self.settingsDict['short.title']
    # end of TheWordBible.load
# end of TheWordBible class



def testTWB( TWBfolder, TWBfilename ):
    # Crudely demonstrate the TheWord Bible class
    import VerseReferences
    #testFolder = "../../../../../Data/Work/Bibles/TheWord modules/" # Must be the same as below

    #TUBfolder = os.path.join( TWBfolder, TWBfilename )
    if Globals.verbosityLevel > 1: print( _("Demonstrating the theWord Bible class...") )
    if Globals.verbosityLevel > 0: print( "  Test folder is '{}' '{}'".format( TWBfolder, TWBfilename ) )
    tWb = TheWordBible( TWBfolder, TWBfilename )
    tWb.load() # Load and process the file
    if Globals.verbosityLevel > 1: print( tWb ) # Just print a summary
    if 0 and tWb:
        if Globals.strictCheckingFlag: tWb.check()
        for reference in ( ('OT','GEN','1','1'), ('OT','GEN','1','3'), ('OT','PSA','3','0'), ('OT','PSA','3','1'), \
                            ('OT','DAN','1','21'),
                            ('NT','MAT','3','5'), ('NT','JDE','1','4'), ('NT','REV','22','21'), \
                            ('DC','BAR','1','1'), ('DC','MA1','1','1'), ('DC','MA2','1','1',), ):
            (t, b, c, v) = reference
            if t=='OT' and len(tWb)==27: continue # Don't bother with OT references if it's only a NT
            if t=='NT' and len(tWb)==39: continue # Don't bother with NT references if it's only a OT
            if t=='DC' and len(tWb)<=66: continue # Don't bother with DC references if it's too small
            svk = VerseReferences.SimpleVerseKey( b, c, v )
            #print( svk, ob.getVerseDataList( reference ) )
            shortText, verseText = svk.getShortText(), tWb.getVerseText( svk )
            if Globals.verbosityLevel > 1: print( reference, shortText, verseText )

        # Now export the Bible and compare the round trip
        tWb.totheWord()
        #doaResults = tWb.doAllExports()
        if Globals.strictCheckingFlag: # Now compare the original and the derived USX XML files
            outputFolder = "OutputFiles/BOS_theWord_Reexport/"
            if Globals.verbosityLevel > 1: print( "\nComparing original and re-exported theWord files..." )
            result = Globals.fileCompare( TWBfilename, TWBfilename, TWBfolder, outputFolder )
            if Globals.debugFlag:
                if not result: halt
# end of testTWB


def demo():
    """
    Main program to handle command line parameters and then run what they want.
    """
    if Globals.verbosityLevel > 0: print( ProgNameVersion )


    if 1: # demo the functions
        #print( theWordGetBBBCV( 1532 ) )
        assert( theWordGetBBBCV( 0 ) == ('GEN', 1, 1) )
        assert( theWordGetBBBCV( 1532 ) == ('GEN', 50, 26) )
        assert( theWordGetBBBCV( 1533 ) == ('EXO', 1, 1) )



    if 1: # demo the file checking code -- first with the whole folder and then with only one folder
        #testFolder = "../../../../../Data/Work/Bibles/theWord modules/"
        testFolder = "Tests/DataFilesForTests/theWordTest/"
        result1 = TheWordBibleFileCheck( testFolder )
        if Globals.verbosityLevel > 1: print( "TestA1", result1 )
        result2 = TheWordBibleFileCheck( testFolder, autoLoad=True )
        if Globals.verbosityLevel > 1: print( "TestA2", result2 )


    if 1: # all discovered modules in the round-trip folder
        testFolder = "Tests/DataFilesForTests/theWordRoundtripTestFiles/"
        foundFolders, foundFiles = [], []
        if os.access( testFolder, os.R_OK ):
            for something in sorted( os.listdir( testFolder ) ):
                somepath = os.path.join( testFolder, something )
                if os.path.isdir( somepath ): foundFolders.append( something )
                elif os.path.isfile( somepath ):
                    if somepath.endswith('.ont') or somepath.endswith('.ot') or somepath.endswith('.nt'):
                        foundFiles.append( something )

            if Globals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
                if Globals.verbosityLevel > 1: print( "\nTrying all {} discovered modules...".format( len(foundFolders) ) )
                parameters = [filename for filename in sorted(foundFiles)]
                with multiprocessing.Pool( processes=Globals.maxProcesses ) as pool: # start worker processes
                    results = pool.map( testTWB, parameters ) # have the pool do our loads
                    assert( len(results) == len(parameters) ) # Results (all None) are actually irrelevant to us here
            else: # Just single threaded
                for j, someFile in enumerate( sorted( foundFiles ) ):
                    if Globals.verbosityLevel > 1: print( "\ntW C{}/ Trying {}".format( j+1, someFile ) )
                    #myTestFolder = os.path.join( testFolder, someFolder+'/' )
                    testTWB( testFolder, someFile )
                    #break # only do the first one.........temp
        else: print( "Sorry, test folder '{}' is not readable on this computer.".format( testFolder ) )

    if 1: # all discovered modules in the test folder
        testFolder = "../../../../../Data/Work/Bibles/theWord modules/"
        foundFolders, foundFiles = [], []
        if os.access( testFolder, os.R_OK ):
            for something in sorted( os.listdir( testFolder ) ):
                somepath = os.path.join( testFolder, something )
                if os.path.isdir( somepath ): foundFolders.append( something )
                elif os.path.isfile( somepath ): foundFiles.append( something )

            if Globals.maxProcesses > 1: # Get our subprocesses ready and waiting for work
                if Globals.verbosityLevel > 1: print( "\nTrying all {} discovered modules...".format( len(foundFolders) ) )
                parameters = [filename for filename in sorted(foundFiles)]
                with multiprocessing.Pool( processes=Globals.maxProcesses ) as pool: # start worker processes
                    results = pool.map( testTWB, parameters ) # have the pool do our loads
                    assert( len(results) == len(parameters) ) # Results (all None) are actually irrelevant to us here
            else: # Just single threaded
                for j, someFile in enumerate( sorted( foundFiles ) ):
                    #if 'web' not in someFile: continue # Just try this module
                    if Globals.verbosityLevel > 1: print( "\ntW D{}/ Trying {}".format( j+1, someFile ) )
                    #myTestFolder = os.path.join( testFolder, someFolder+'/' )
                    testTWB( testFolder, someFile )
                    #break # only do the first one.........temp
        else: print( "Sorry, test folder '{}' is not readable on this computer.".format( testFolder ) )
# end of demo

if __name__ == '__main__':
    # Configure basic set-up
    parser = Globals.setup( ProgName, ProgVersion )
    Globals.addStandardOptionsAndProcess( parser )

    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    demo()

    Globals.closedown( ProgName, ProgVersion )
# end of TheWordBible.py