from urllib.parse import urlencode
from _verify_dataset_api import verify


def cases(expected):
    return [('/api/v1/reports?'+urlencode({'from': report['from'], 'to': report['to']}),
             {key: value for key, value in report.items() if key != 'name'}) for report in expected['reports']]


if __name__ == '__main__':
    verify(cases, page='/reports', invalid_paths=['/api/v1/reports?from=2026-11-16&to=2026-11-15'], story='BB-24')
