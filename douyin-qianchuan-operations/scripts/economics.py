#!/usr/bin/env python3
"""Calculate contribution and matched ROI thresholds for one declared order scope."""
import json
import math
import sys
from decimal import Decimal, InvalidOperation


def amount(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        raise ValueError(f"{name}: must be a finite nonnegative amount")
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"{name}: invalid amount") from exc
    if not result.is_finite() or result < 0:
        raise ValueError(f"{name}: must be finite and nonnegative")
    return result


def calculate(data):
    if not isinstance(data, dict):
        raise ValueError("input must be an object")
    if not isinstance(data.get("scope"), str) or not data["scope"].strip():
        raise ValueError("scope: describe order/date scope and omitted costs")
    paid = amount(data["paid_amount"], "paid_amount")
    refunds = amount(data["refund_amount"], "refund_amount")
    spend = amount(data["ad_spend"], "ad_spend")
    costs = data["non_ad_costs"]
    if not isinstance(costs, dict) or not costs:
        raise ValueError("non_ad_costs: provide an explicit nonempty cost breakdown")
    cost_total = sum((amount(v, f"non_ad_costs.{k}") for k, v in costs.items()), Decimal(0))
    if refunds > paid:
        raise ValueError("refund_amount exceeds paid_amount; check the order scope")
    net = paid - refunds
    contribution = net - cost_total

    def number(value):
        result = float(round(value, 6))
        if not math.isfinite(result):
            raise ValueError("amount exceeds supported output range")
        return result

    def ratio(numerator, denominator):
        return number(numerator / denominator) if denominator > 0 else None

    return {
        "scope": data["scope"],
        "net_revenue": number(net),
        "non_ad_cost_total": number(cost_total),
        "contribution_before_ads": number(contribution),
        "contribution_after_ads": number(contribution - spend),
        "paid_roi": ratio(paid, spend),
        "net_revenue_roi": ratio(net, spend),
        "break_even_paid_roi": ratio(paid, contribution),
        "break_even_net_revenue_roi": ratio(net, contribution),
        "max_ad_spend_at_break_even": number(max(Decimal(0), contribution)),
        "positive_contribution_before_ads": contribution > 0,
        "note": "Only the supplied costs are included. Null ROI means denominator is nonpositive; inputs are not independently verified."
    }


def main():
    if len(sys.argv) != 2:
        print("usage: python3 economics.py INPUT.json", file=sys.stderr)
        return 2
    try:
        with open(sys.argv[1], encoding="utf-8") as handle:
            result = calculate(json.load(handle))
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError, ArithmeticError) as exc:
        print(f"input error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
