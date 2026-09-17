"""Unit tests for calculation_service — no DB needed."""
import pytest
from decimal import Decimal
from services.calculation_service import (
    calculate_total_area, calculate_inverter_capacity,
    calculate_addon_total, calculate_subtotal,
    calculate_discount_amount, calculate_grand_total,
    calculate_payment_total, calculate_all,
)


# ---------------------------------------------------------------------------
# calculate_total_area
# ---------------------------------------------------------------------------

def test_total_area_standard():
    assert calculate_total_area(Decimal('5')) == Decimal('400.00')
    assert calculate_total_area(Decimal('3')) == Decimal('240.00')
    assert calculate_total_area(Decimal('10')) == Decimal('800.00')
    assert calculate_total_area(Decimal('1.5')) == Decimal('120.00')


def test_total_area_large():
    assert calculate_total_area(Decimal('100')) == Decimal('8000.00')


def test_total_area_fractional():
    assert calculate_total_area(Decimal('0.01')) == Decimal('0.80')


# ---------------------------------------------------------------------------
# calculate_inverter_capacity
# ---------------------------------------------------------------------------

def test_inverter_equals_plant_capacity():
    assert calculate_inverter_capacity(Decimal('5')) == Decimal('5.00')
    assert calculate_inverter_capacity(Decimal('3.5')) == Decimal('3.50')
    assert calculate_inverter_capacity(Decimal('0.01')) == Decimal('0.01')


# ---------------------------------------------------------------------------
# calculate_addon_total
# ---------------------------------------------------------------------------

def test_addon_total_empty():
    assert calculate_addon_total([]) == Decimal('0.00')


def test_addon_total_single():
    assert calculate_addon_total([{'amount': 10000}]) == Decimal('10000.00')


def test_addon_total_multiple():
    addons = [{'amount': 10000}, {'amount': 5000}, {'amount': 2500}]
    assert calculate_addon_total(addons) == Decimal('17500.00')


def test_addon_total_zero_amounts():
    addons = [{'amount': 0}, {'amount': 0}]
    assert calculate_addon_total(addons) == Decimal('0.00')


def test_addon_total_mixed_zero():
    addons = [{'amount': 5000}, {'amount': 0}, {'amount': 3000}]
    assert calculate_addon_total(addons) == Decimal('8000.00')


# ---------------------------------------------------------------------------
# calculate_subtotal
# ---------------------------------------------------------------------------

def test_subtotal_no_addons():
    assert calculate_subtotal(Decimal('100000'), Decimal('0')) == Decimal('100000.00')


def test_subtotal_with_addons():
    assert calculate_subtotal(Decimal('100000'), Decimal('17500')) == Decimal('117500.00')


# ---------------------------------------------------------------------------
# calculate_discount_amount
# ---------------------------------------------------------------------------

def test_discount_zero():
    assert calculate_discount_amount(Decimal('100000'), Decimal('0')) == Decimal('0.00')


def test_discount_ten_percent():
    assert calculate_discount_amount(Decimal('100000'), Decimal('10')) == Decimal('10000.00')


def test_discount_100_percent():
    assert calculate_discount_amount(Decimal('100000'), Decimal('100')) == Decimal('100000.00')


def test_discount_fractional_percent():
    result = calculate_discount_amount(Decimal('100000'), Decimal('5.5'))
    assert result == Decimal('5500.00')


# ---------------------------------------------------------------------------
# calculate_grand_total
# ---------------------------------------------------------------------------

def test_grand_total_no_discount():
    assert calculate_grand_total(Decimal('100000'), Decimal('0')) == Decimal('100000.00')


def test_grand_total_with_discount():
    assert calculate_grand_total(Decimal('100000'), Decimal('10000')) == Decimal('90000.00')


def test_grand_total_100_percent_discount():
    assert calculate_grand_total(Decimal('100000'), Decimal('100000')) == Decimal('0.00')


# ---------------------------------------------------------------------------
# calculate_payment_total
# ---------------------------------------------------------------------------

def test_payment_total_empty():
    assert calculate_payment_total([]) == Decimal('0.00')


def test_payment_total_single():
    assert calculate_payment_total([{'amount': 90000}]) == Decimal('90000.00')


def test_payment_total_multiple():
    payments = [{'amount': 50000}, {'amount': 40000}]
    assert calculate_payment_total(payments) == Decimal('90000.00')


# ---------------------------------------------------------------------------
# calculate_all — integration
# ---------------------------------------------------------------------------

def test_calculate_all_no_addons_no_payments():
    calcs, errors = calculate_all(5.0, 200000, [], 0, [])
    assert errors == []
    assert calcs['total_area'] == Decimal('400.00')
    assert calcs['inverter_capacity'] == Decimal('5.00')
    assert calcs['grand_total'] == Decimal('200000.00')
    assert calcs['payment_total'] == Decimal('0.00')


def test_calculate_all_payment_match():
    # base=100000, addon=5000, subtotal=105000, disc=10%=10500, grand=94500
    addons = [{'amount': 5000}]
    payments = [{'amount': 94500}]
    calcs, errors = calculate_all(5.0, 100000, addons, 10.0, payments)
    assert errors == []
    assert calcs['grand_total'] == Decimal('94500.00')


def test_calculate_all_payment_mismatch():
    addons = [{'amount': 5000}]
    payments = [{'amount': 50000}]  # too low
    _, errors = calculate_all(5.0, 100000, addons, 10.0, payments)
    assert len(errors) == 1
    assert 'does not match' in errors[0]


def test_calculate_all_no_discount():
    calcs, _ = calculate_all(3.0, 150000, [], 0.0, [])
    assert calcs['discount_amount'] == Decimal('0.00')
    assert calcs['grand_total'] == Decimal('150000.00')


def test_calculate_all_100_percent_discount():
    calcs, errors = calculate_all(5.0, 100000, [], 100.0, [])
    assert errors == []
    assert calcs['grand_total'] == Decimal('0.00')


def test_calculate_all_large_system():
    calcs, errors = calculate_all(100.0, 5500000, [], 0, [])
    assert errors == []
    assert calcs['total_area'] == Decimal('8000.00')
    assert calcs['inverter_capacity'] == Decimal('100.00')


def test_calculate_all_multiple_addons_and_payments():
    addons = [{'amount': 10000}, {'amount': 5000}]
    # base=200000, addon=15000, subtotal=215000, disc=0, grand=215000
    payments = [{'amount': 107500}, {'amount': 107500}]
    calcs, errors = calculate_all(5.0, 200000, addons, 0, payments)
    assert errors == []
    assert calcs['addon_total'] == Decimal('15000.00')
    assert calcs['grand_total'] == Decimal('215000.00')
    assert calcs['payment_total'] == Decimal('215000.00')


def test_calculate_all_empty_payments_no_error():
    """Empty payments list should not trigger a mismatch error."""
    _, errors = calculate_all(5.0, 100000, [], 0, [])
    assert errors == []
