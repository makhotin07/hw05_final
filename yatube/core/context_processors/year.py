from datetime import datetime


def year(request):
    year_dt = datetime.now().year
    return {
        'year': year_dt
    }
