# Age calculation
def calculateAge(timedelta_obj):
    total_seconds = timedelta_obj.total_seconds()

    if total_seconds < 60:
        return str(int(total_seconds)) + "s"
    elif total_seconds < 3600:
        return str(int(total_seconds/60)) + "m"
    elif total_seconds < 86400:
        return str(int(total_seconds/3600)) + "h"
    else:
        return str(timedelta_obj.days) + "d"
    

def filter_annotations(annotations):
    if not annotations:
        return None
    filtered_annotations = {k: v for k, v in annotations.items() if k != "kubectl.kubernetes.io/last-applied-configuration"} 
    return filtered_annotations if filtered_annotations else None
