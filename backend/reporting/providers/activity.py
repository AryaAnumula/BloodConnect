from reporting.providers import invoke


def collection_wastage(*, start, end):
    return invoke('inventory.selectors.reporting', 'collection_wastage_totals', start=start, end=end)


def issue_totals(*, start, end):
    return invoke('blood_requests.selectors.reporting', 'request_issue_totals', start=start, end=end)
