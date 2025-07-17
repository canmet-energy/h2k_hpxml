def get_val(obj, path):
    for key in path.split(","):
        # returns itself if nothing found so we can use paths containing higher level info
        obj = obj.get(key, obj)

    return obj
