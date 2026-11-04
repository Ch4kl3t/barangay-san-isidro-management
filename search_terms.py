"""Bounded literal word search; callers supply only source-owned SQL expressions."""
import unicodedata

def words(value):
    text=unicodedata.normalize('NFC',str(value or ''))[:200]
    return list(dict.fromkeys(text.replace(',', ' ').split()))[:20]

def literal_pattern(word):
    return '%' + word.replace('\\','\\\\').replace('%','\\%').replace('_','\\_') + '%'

def add_search(clauses,params,expression,value):
    for word in words(value):
        clauses.append(expression + ' ILIKE %s')
        params.append(literal_pattern(word))
