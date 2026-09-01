"""Unit tests for calculation_service."""
import pytest
from decimal import Decimal
from services.calculation_service import (
    calculate_total_area, calculate_inverter_capacity,
    calculate_addon_total, calculate_subtotal,
    calculate_discount_amount, calculate_grand_total,
    calculate_payment_total, calculate_all
)


def test_total_area():
    assert calculate_total_area(Decimal('5')) == Decimal('400.00')
    assert calculate_total_area(Decimal('3')) == Decimal('240.00')
    assert calculate_total_area(Decimal('10')) == Decimal('800.00')
    assert calculate_total_area(Decimal('1.5')) == Decimal('120.00')


def test_inverter_capacity():
    assert calculate_inverter_capacity(Decimal('5')) == Decimal('5.00')
    assert calculate_inverter_capacity(Decimal('3.5')) == Decimal('3.50')


def test_addon_total_empty():
    assert calculate_addon_total([]) == Decimal('0.00')


def test_addon_total():
    addons = [{'amount': 10000}, {'amount': 5000}, {'amount': 2500}]
    assert calculate_addon_total(addons) == Decimal('17500.00')


def test_subtotal():
    assert calculate_subtotal(Decimal('100000'), Decimal('17500')) == Decimal('117500.00')


def test_discount_amount():
    assert calculate_discount_amount(Decimal('100000'), Decimal('10')) == Decimal('10000.00')
    assert calculate_discount_amount(Decimal('100000'), Decimal('0')) == Decimal('0.00')


def test_grand_total():
    assert calculate_grand_total(Decimal('100000'), Decimal('10000')) == Decimal('90000.00')


def test_payment_total():
    payments = [{'amount': 50000}, {'amount': 40000}]
    assert calculate_payment_total(payments) == Decimal('90000.00')


def test_payment_mismatch():
    addons = [{'amount': 5000}]
    payments = [{'amount': 50000}]  # Wrong total
    _, errors = calculate_all(5.0, 100000, addons, 10.0, payments)
    assert len(errors) == 1
    assert 'does not match' in errors[0]


def test_payment_match():
    addons = [{'amount': 5000}]
    # base=100000, addon=5000, subtotal=105000, disc=10%=10500, grand=94500
    payments = [{'amount': 94500}]
    calcs, errors = calculate_all(5.0, 100000, addons, 10.0, payments)
    assert len(errors) == 0
    assert calcs['grand_total'] == Decimal('94500.00')


def test_calculate_all_no_payments():
    calcs, errors = calculate_all(5.0, 200000, [], 0, [])
    assert errors == []
    assert calcs['total_area'] == Decimal('400.00')
    assert calcs['inverter_capacity'] == Decimal('5.00')
    assert calcs['grand_total'] == Decimal('200000.00')


def test_zero_discount():
    calcs, _ = calculate_all(3.0, 150000, [], 0.0, [])
    assert calcs['discount_amount'] == Decimal('0.00')
    assert calcs['grand_total'] == Decimal('150000.00')
