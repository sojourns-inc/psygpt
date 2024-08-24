from collections import defaultdict
from datetime import datetime, timedelta


class RateLimiter:
    def __init__(self, max_requests, window_size):
        self.requests = {}
        self.max_requests = max_requests
        self.window_size = window_size

    def allow_request(self, key):
        current_time = datetime.now()
        if key not in self.requests:
            self.requests[key] = []
        self.requests[key] = [
            t for t in self.requests[key] if t > current_time - self.window_size
        ]

        if len(self.requests[key]) < self.max_requests:
            self.requests[key].append(current_time)
            return True
        return False


def calc_downtime():
    future_date = datetime(year=2024, month=8, day=24, hour=05, minute=00)
    now = datetime.now()
    difference = future_date - now
    total_seconds = difference.total_seconds()

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60

    return f"{int(hours)} hours and {int(minutes)} minutes"


class MultiKeyDict:
    def __init__(self):
        self.data = {}
        self.key_map = defaultdict(list)

    def add(self, keys, value):
        for key in keys:
            self.data[key] = value
            self.key_map[value].append(key)

    def get(self, key):
        return self.data.get(key, None)
