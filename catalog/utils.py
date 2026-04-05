from django.db.models import Q

def get_smart_search_filter(query_str, search_fields):
    """
    Returns a Q object that matches if ALL words in query_str 
    are present in AT LEAST ONE of search_fields.
    Example: 'Подушка fit' -> matches if 'подушка' is in (name OR oem) 
    AND 'fit' is in (name OR oem).
    """
    if not query_str:
        return Q()
        
    words = query_str.split()
    q_all_words = Q()
    
    for word in words:
        if not word:
            continue
        q_any_field = Q()
        for field in search_fields:
            # Handle potential list/tuple for exact matches or other lookups
            if isinstance(field, (list, tuple)):
                # Not used currently but for future extensibility
                pass
            else:
                q_any_field |= Q(**{f"{field}__icontains": word})
        
        # Word must match at least one field (OR logic within word)
        # All words must be present (AND logic between words)
        if q_all_words:
            q_all_words &= q_any_field
        else:
            q_all_words = q_any_field
            
    return q_all_words
