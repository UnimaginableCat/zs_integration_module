from enum import Enum


class TimeInterval(Enum):
    """Price and quantity sync time intervals."""
    one_min = '1 minute'
    five_minutes = '5 minutes'
    fifteen_minutes = '15 minutes'
    one_hour = '1 hour'
    one_day = '1 day'


class TaskStatus(Enum):
    active = 'Active'
    disabled = 'Disabled'
