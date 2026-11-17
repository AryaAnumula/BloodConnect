from _verify_dataset_api import verify


def cases(expected):
    return [('/api/v1/dashboard', expected['dashboard'])]


if __name__ == '__main__':
    verify(cases, page='/dashboard', invalid_paths=['/api/v1/dashboard?unexpected=1'], story='BB-23')
