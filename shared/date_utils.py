"""
Date calculation utilities for fund liquidation timelines.
"""
from datetime import timedelta

import pandas as pd


def add_business_days(start_date, num_days, count_type="Úteis"):
    """Add business or calendar days to a date."""
    if num_days == 0:
        return start_date
    if count_type == "Úteis":
        current = start_date
        added = 0
        while added < num_days:
            current += timedelta(days=1)
            if current.weekday() < 5:
                added += 1
        return current
    else:
        return start_date + timedelta(days=num_days)


def subtract_business_days(end_date, num_days, count_type="Úteis"):
    """Subtract business or calendar days from a date."""
    if num_days == 0:
        return end_date
    if count_type == "Úteis":
        current = end_date
        subtracted = 0
        while subtracted < num_days:
            current -= timedelta(days=1)
            if current.weekday() < 5:
                subtracted += 1
        return current
    else:
        return end_date - timedelta(days=num_days)


def compute_settle_date(request_date, conv_days, liq_days, count_type):
    """Compute liquidation date: request -> cotização -> liquidação."""
    cot = add_business_days(request_date, conv_days, count_type)
    return add_business_days(cot, liq_days, count_type)


def compute_latest_request_date(target_date, conv_days, liq_days, count_type):
    """Latest possible request date so that money settles by target_date."""
    pre_liq = subtract_business_days(target_date, liq_days, count_type)
    return subtract_business_days(pre_liq, conv_days, count_type)
