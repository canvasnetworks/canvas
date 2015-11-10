"""
Stats library
Sources: 
http://www.wmps.com/blog/website-analysis/web-analytics/statistics-and-web-analytics-hypothesis-testing/
http://www.wmps.com/blog/website-analysis/web-analytics/hypothesis-testing-in-ab-testing/
"""
from math import sqrt

# http://www.sjsu.edu/faculty/gerstman/EpiInfo/z-table.htm
z_table_90_perc = [
    (0.0, 0.5359),
    (0.1, 0.5753),
    (0.2, 0.6141),
    (0.3, 0.6517),
    (0.4, 0.6879),
    (0.5, 0.7224),
    (0.6, 0.7549),
    (0.7, 0.7852),
    (0.8, 0.8133),
    (0.9, 0.8389),
    (1.0, 0.8621),
    (1.1, 0.8830),
    (1.2, 0.9015),
    (1.3, 0.9177),
    (1.4, 0.9319),
    (1.5, 0.9441),
    (1.6, 0.9545),
    (1.7, 0.9633),
    (1.8, 0.9706),
    (1.9, 0.9767),
    (2.0, 0.9817),
    (2.1, 0.9857),
    (2.2, 0.9890),
    (2.3, 0.9916),
    (2.4, 0.9936),
    (2.5, 0.9952),
    (2.6, 0.9964),
    (2.7, 0.9974),
    (2.8, 0.9981),
    (2.9, 0.9986),
    (3.0, 0.9990)
]

def z_to_ci(z):
    if z == 0:
        return 0
        
    z = abs(z)
    for z_interval, perc in z_table_90_perc:
        if z_interval <= z < (z_interval + 0.1):
            return perc
    return 0.9990

def z_test(sample_conversions, sample_size, expected_conversions, expected_size):
    """
    Returns std deviations from the expected mean, assuming a normal distribution.
    95% = +/- 1.645
    """
    
    # Division by zero guards, in all of these cases z-test fails because distribution is not sufficiently binomial
    if not sample_size or not expected_size or not (sample_conversions + expected_conversions):
        return 0
        
    if sample_size == sample_conversions or expected_conversions == expected_size:
        return 0

    sample_mean = float(sample_conversions) / sample_size
    expected_mean = float(expected_conversions) / expected_size
    term = lambda p,n: (p * (1 - p)) / n
    
    return (sample_mean - expected_mean) / sqrt(term(sample_mean, sample_size) + term(expected_mean, expected_size))

def percentile(items, percentile):
    items = sorted(items)
    index = int(len(items) * (percentile / 100.0))
    return items[index]

def _pp(items, p):
    print "%sth:\t%s" % (p,percentile(items, p))

def pp_percentiles(items):
    print "Percentiles:"
    _pp(items, 50)
    _pp(items, 90)
    _pp(items, 95)
    _pp(items, 99)
    _pp(items, 99.9)

def pp_long_percentiles(items):
    print "Percentiles:"
    for x in range(10):
        _pp(items, x*10)
    _pp(items, 95)
    _pp(items, 99)
    _pp(items, 99.9)

