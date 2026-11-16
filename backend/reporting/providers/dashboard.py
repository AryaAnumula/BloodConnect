from reporting.providers import invoke


def current_stock(*, actor):
    return invoke('inventory.selectors.stock', 'stock_summary', actor=actor,
                  filters={}, page=1, page_size=100)


def pending_requests():
    return invoke('blood_requests.selectors.reporting', 'pending_request_count')


def upcoming_camps(*, now):
    return invoke('scheduling.selectors.summary', 'upcoming_camp_count', now=now)
