from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any, Tuple

AREA_FACTOR = Decimal('80')


def calculate_total_area(plant_capacity_kw: Decimal) -> Decimal:
    return (plant_capacity_kw * AREA_FACTOR).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calculate_inverter_capacity(plant_capacity_kw: Decimal) -> Decimal:
    return plant_capacity_kw.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calculate_addon_total(addons: List[Dict[str, Any]]) -> Decimal:
    total = Decimal('0')
    for addon in addons:
        total += Decimal(str(addon.get('amount', 0)))
    return total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calculate_subtotal(base_price: Decimal, addon_total: Decimal) -> Decimal:
    return (base_price + addon_total).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calculate_discount_amount(subtotal: Decimal, discount_percent: Decimal) -> Decimal:
    return (subtotal * discount_percent / Decimal('100')).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP)


def calculate_grand_total(subtotal: Decimal, discount_amount: Decimal) -> Decimal:
    return (subtotal - discount_amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calculate_payment_total(payments: List[Dict[str, Any]]) -> Decimal:
    total = Decimal('0')
    for p in payments:
        total += Decimal(str(p.get('amount', 0)))
    return total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calculate_all(
    plant_capacity_kw: float,
    base_price: float,
    addons: List[Dict[str, Any]],
    discount_percent: float,
    payments: List[Dict[str, Any]]
) -> Tuple[Dict[str, Decimal], List[str]]:
    errors = []
    capacity = Decimal(str(plant_capacity_kw))
    price = Decimal(str(base_price))
    disc = Decimal(str(discount_percent))

    total_area = calculate_total_area(capacity)
    inverter_capacity = calculate_inverter_capacity(capacity)
    addon_total = calculate_addon_total(addons)
    subtotal = calculate_subtotal(price, addon_total)
    discount_amount = calculate_discount_amount(subtotal, disc)
    grand_total = calculate_grand_total(subtotal, discount_amount)
    payment_total = calculate_payment_total(payments)

    if payments and payment_total != grand_total:
        errors.append(
            f'Payment total (₹{payment_total:,.2f}) does not match Grand Total '
            f'(₹{grand_total:,.2f}). Difference: ₹{abs(grand_total - payment_total):,.2f}'
        )

    return {
        'total_area': total_area,
        'inverter_capacity': inverter_capacity,
        'addon_total': addon_total,
        'subtotal': subtotal,
        'discount_amount': discount_amount,
        'grand_total': grand_total,
        'payment_total': payment_total,
    }, errors
