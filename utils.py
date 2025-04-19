def get_val_or_default(dict_obj, key_path, default=None):
    """
    Safely retrieve a value from a nested dictionary, returning a default if the path doesn't exist.
    
    Args:
        dict_obj: The dictionary to query.
        key_path: A string with dot notation (e.g., 'a.b.c') or list of keys.
        default: Value to return if the key path is invalid (default: None).
    
    Returns:
        The value at the key path or the default value.
    """
    if isinstance(key_path, str):
        key_path = key_path.split('.')

    temp_dict = dict_obj
    for key in key_path:
        if isinstance(temp_dict, dict) and key in temp_dict:
            temp_dict = temp_dict[key]
        else:
            return default
    return temp_dict
