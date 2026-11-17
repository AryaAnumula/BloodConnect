from reporting.exceptions import ReportingUnavailable


def nonnegative(value):
    if type(value) is not int or value < 0:
        raise ReportingUnavailable()
    return value
