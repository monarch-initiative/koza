

global_translation = {}
file = {}
# Nodes

#hp_term = Node
#publications: List[Publication] = []
# #disease = Disease


for pub in file['Publications'].split(';'):

    publication.id = pub

    if pub.startswith('PMID:'):
        publication.type = global_translation['journal article']

    elif pub.startswith('ISBN'):
        publication.type = global_translation['publication']

    elif pub.startswith('OMIM:'):
        publication.type = global_translation['web page']

    elif pub.startswith('DECIPHER:'):
        publication.type = global_translation['web page']

    elif pub.startswith('ORPHA:'):
        publication.type = global_translation['web page']

    elif pub.startswith('http'):
        publication.type = global_translation['web page']

    else:
        pass
        # not mapped warning

# Edges

if file['Aspect'] == 'P':
    pass

elif file['Aspect'] == 'M':
    pass

elif file['Aspect'] == 'I':
    pass

elif file['Aspect'] == 'C':
    pass