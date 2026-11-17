from rest_framework.exceptions import APIException


class ReportingUnavailable(APIException):
    status_code = 503
    default_code = 'reporting_unavailable'
    default_detail = 'Report data is not available yet. Please try again later.'
