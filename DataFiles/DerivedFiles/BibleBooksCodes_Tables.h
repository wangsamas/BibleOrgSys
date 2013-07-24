// ./DataFiles/DerivedFiles/BibleBooksCodes_Tables.h
//
// This UTF-8 file was automatically generated by BibleBooksCodes.py V0.69 on 2013-07-24 22:30:35.824980
//
// Bible books codes list data
//  Version: 0.70
//  Date: 2013-07-24
//

#ifndef BIBLEBOOKSCODES_Tables_h
#define BIBLEBOOKSCODES_Tables_h

typedef struct allAbbreviationsDictEntryStruct {
    const unsigned char* abbreviation;
    const unsigned char referenceAbbreviation[3+1];
} allAbbreviationsDictEntry;

typedef struct SBLAbbreviationDictEntryStruct {
    const unsigned char* SBLAbbreviation;
    const int referenceNumber;
    const unsigned char referenceAbbreviation[3+1];
} SBLAbbreviationDictEntry;

