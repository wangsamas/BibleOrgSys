//DerivedFiles/BibleBookOrders_Tables.h
//
// This UTF-8 file was automatically generated by BibleBookOrders.py V0.80 on 2011-02-03 14:29:27.567855
//

#ifndefBIBLEBOOKORDERS_Tables_h
#defineBIBLEBOOKORDERS_Tables_h

typedef structbookOrderByRefEntryStruct {
   const unsigned char referenceAbbreviation[3+1];
   const int indexNumber;
}bookOrderByRefEntry;

typedef structbookOrderByIndexEntryStruct {
   const int indexNumber;
   const unsigned char referenceAbbreviation[3+1];
}bookOrderByIndexEntry;

typedef structtableEntryStruct {
   const unsigned char* systemName;
   bookOrderByRefEntry* byReference;
   bookOrderByIndexEntry* byBook;
}tableEntry;

#endif //BIBLEBOOKORDERS_Tables_h

// end ofBibleBookOrders_Tables.h