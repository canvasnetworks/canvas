import datetime, time


def days(max_days=28):
    for i in reversed(range(max_days)):
        yield datetime.datetime.today() - datetime.timedelta(i)

def days_ytd():
    today = datetime.datetime.now()
    day = datetime.datetime(today.year, 1, 1)
    while day < today:
        yield day
        day += datetime.timedelta(1)

def hours():
    for h in reversed(range(48)):
        yield datetime.datetime.now() - datetime.timedelta(hours=h)

def jstime_from_dt(dt):
    return time.mktime(dt.timetuple()) * 1000

