# Age calculation
def calculateAge(timedelta_obj):
    total_seconds = timedelta_obj.total_seconds()

    if total_seconds < 60:
        return str(int(total_seconds)) + "s"
    elif total_seconds < 3600:
        return str(int(total_seconds/60)) + "m"
    elif total_seconds < 86400:
        str(int(total_seconds/3600)) + "h"
    else:
        return str(timedelta_obj.days) + "d"