#!/usr/bin/env python3
"""
Generate test ONGRID and HYBRID PDFs to verify visual quality.
Run: python tests/generate_test_pdfs.py
Output: test_ongrid.pdf, test_hybrid.pdf in project root
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decimal import Decimal
from datetime import date
from app import create_app, db
from config import TestingConfig
from models.user import User
from models.template import Template
from models.company import CompanySetting
from models.proposal import (
    Proposal, ProposalModule, ProposalBattery,
    ProposalAddon, ProposalPayment
)
from services.pdf_service import generate_pdf_for_proposal
from werkzeug.security import generate_password_hash
import shutil


def seed_company(app):
    settings = {
        'company_name': 'Sologix Energy Private Limited',
        'company_address_line1': '2nd Floor, Tower Two',
        'company_address_line2': 'Software Technology Park of India,',
        'company_address_line3': 'Namkum Industrial Area, Ranchi',
        'company_address_line4': 'Jharkhand- 834010',
        'company_gstin': '20AAZCS9296C1ZT',
        'company_pan': 'AAZCS9296C',
        'bank_name': 'Canara Bank, Chutia, Ranchi, Jharkhand - 834001',
        'bank_account_number': '125009426214',
        'bank_account_name': 'Sologix Energy Private Limited',
        'bank_ifsc': 'CNRB0001969',
        'bank_upi_id': '8287766474@okbizaxis',
        'cfa_amount': '78000',
        'tilt_angle': '15-22 degrees',
        'dcr_module_wattage': '580W-620W',
        'ndcr_module_wattage': '580W-620W',
        'module_makes': 'Rayzon Solar/Premier Energy/RenewSys/Pahal/Adani/TATA Power',
        'inverter_makes': 'Growatt/Deye',
        'mounting_structure_make': 'HDGI',
        'battery_chemistry': 'FeLiO4P',
        'earthing_quantity': '3 nos.',
        'lightning_arrestor_quantity': '1 no.',
        'warranty_module_defect': '12 Years warranty on solar modules against manufacturing defects',
        'warranty_module_performance': '30 Years linear performance guarantee on solar modules',
        'warranty_inverter': '8 years warranty on solar on-grid Inverters.',
        'note_approach': 'Easy approach to the work site to be provided by the consumer.',
        'note_shadow': 'Shadow free space on the roof should be provided for the installation of solar panels.',
        'note_sim': 'Sim Data Service for remote monitoring is free for the first year. Thereafter a charge of Rs. 1500 per year.',
        'note_raised_structure': 'The cost of the Raised Structure will be Rs. 5000 per kW.',
        'payment_reminder': 'Details for making payment including in proposal, do not forget to collect receipt of payment.',
        'company_signatory': '2nd Floor, STPI, Namkum, Ranchi- 834010',
    }
    for key, value in settings.items():
        if not CompanySetting.query.filter_by(key=key).first():
            db.session.add(CompanySetting(key=key, value=value))
    db.session.commit()


def create_test_ongrid(master, template):
    p = Proposal(
        proposal_number='SP-2026-00001',
        customer_name='Ramesh Kumar Sharma',
        customer_address='Plot 45, Sector 2, Harmu Housing Colony, Ranchi, Jharkhand - 834002',
        customer_contact='9876543210',
        system_type='ONGRID',
        plant_capacity=Decimal('5.00'),
        total_area=Decimal('400.00'),
        mounting_type='RCC',
        inverter_capacity=Decimal('5.00'),
        base_price=Decimal('285000.00'),
        addon_total=Decimal('15000.00'),
        subtotal=Decimal('300000.00'),
        discount_percent=Decimal('5.00'),
        discount_amount=Decimal('15000.00'),
        grand_total=Decimal('285000.00'),
        status='DRAFT',
        created_by=master.id,
        proposal_date=date(2026, 9, 1),
        template_id=template.id,
        snapshot={}
    )
    db.session.add(p)
    db.session.flush()

    # DCR modules
    db.session.add(ProposalModule(
        proposal_id=p.id, module_type='DCR',
        make='Rayzon Solar', wattage='580W',
        quantity=9
    ))
    # NDCR modules (0 quantity = not used, but present in BOM)
    db.session.add(ProposalModule(
        proposal_id=p.id, module_type='NDCR',
        make='Premier Energy', wattage='600W',
        quantity=0
    ))

    # Addons
    db.session.add(ProposalAddon(
        proposal_id=p.id,
        name='Online Monitoring System (Wi-Fi)',
        amount=Decimal('8000.00'),
        sequence=1
    ))
    db.session.add(ProposalAddon(
        proposal_id=p.id,
        name='Net Meter Application & Assistance',
        amount=Decimal('7000.00'),
        sequence=2
    ))

    # Payments (must sum to grand_total = 285000)
    db.session.add(ProposalPayment(
        proposal_id=p.id,
        milestone='Advance payment at order confirmation',
        amount=Decimal('142500.00'),
        sequence=1
    ))
    db.session.add(ProposalPayment(
        proposal_id=p.id,
        milestone='Payment on delivery of material at site',
        amount=Decimal('85500.00'),
        sequence=2
    ))
    db.session.add(ProposalPayment(
        proposal_id=p.id,
        milestone='Final payment on commissioning',
        amount=Decimal('57000.00'),
        sequence=3
    ))

    db.session.commit()
    return p


def create_test_hybrid(master, template):
    p = Proposal(
        proposal_number='SP-2026-00002',
        customer_name='Sunita Devi Pandey',
        customer_address='Village Karamtoli, PO Namkum, Dist. Ranchi, Jharkhand - 834010',
        customer_contact='9123456789',
        system_type='HYBRID',
        plant_capacity=Decimal('3.00'),
        total_area=Decimal('240.00'),
        mounting_type='SEATMOUNT',
        inverter_capacity=Decimal('3.00'),
        base_price=Decimal('210000.00'),
        addon_total=Decimal('0.00'),
        subtotal=Decimal('210000.00'),
        discount_percent=Decimal('0.00'),
        discount_amount=Decimal('0.00'),
        grand_total=Decimal('210000.00'),
        status='DRAFT',
        created_by=master.id,
        proposal_date=date(2026, 9, 1),
        template_id=template.id,
        snapshot={}
    )
    db.session.add(p)
    db.session.flush()

    # DCR modules
    db.session.add(ProposalModule(
        proposal_id=p.id, module_type='DCR',
        make='Adani Solar', wattage='545W',
        quantity=6
    ))

    # Battery
    db.session.add(ProposalBattery(
        proposal_id=p.id,
        make='Gobel Power',
        capacity_kwh=Decimal('5.12'),
        quantity=1,
        chemistry='LiFePO4'
    ))

    # Payments (must sum to grand_total = 210000)
    db.session.add(ProposalPayment(
        proposal_id=p.id,
        milestone='Advance (50%) at order confirmation',
        amount=Decimal('105000.00'),
        sequence=1
    ))
    db.session.add(ProposalPayment(
        proposal_id=p.id,
        milestone='Balance (50%) on commissioning',
        amount=Decimal('105000.00'),
        sequence=2
    ))

    db.session.commit()
    return p


def main():
    # Use SQLite in-memory for test; PDFs written to test_pdf_output/ in project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(project_root, 'test_pdf_output')
    os.makedirs(output_dir, exist_ok=True)

    class TestPdfConfig(TestingConfig):
        # Absolute path so get_storage_path() resolves correctly regardless of app.root_path
        STORAGE_PATH = output_dir

    app = create_app(TestPdfConfig)

    with app.app_context():
        db.create_all()
        seed_company(app)

        master = User(
            name='Test Master', username='testmaster',
            password_hash=generate_password_hash('testpass'),
            role='MASTER', is_active=True
        )
        db.session.add(master)
        db.session.flush()

        ongrid_tmpl = Template(
            name='Ongrid v1', system_type='ONGRID', version=1,
            is_active=True, html_file='pdf/ongrid.html', created_by=master.id
        )
        hybrid_tmpl = Template(
            name='Hybrid v1', system_type='HYBRID', version=1,
            is_active=True, html_file='pdf/hybrid.html', created_by=master.id
        )
        db.session.add_all([ongrid_tmpl, hybrid_tmpl])
        db.session.commit()

        print('\n--- Generating ONGRID PDF ---')
        ongrid = create_test_ongrid(master, ongrid_tmpl)
        try:
            success, err, pdf_path = generate_pdf_for_proposal(ongrid, master)
            if success and pdf_path:
                dest = os.path.join(output_dir, 'test_ongrid.pdf')
                shutil.copy2(pdf_path, dest)
                print(f'ONGRID PDF saved: {dest}')
            else:
                print(f'ONGRID PDF FAILED: {err}')
        except Exception as e:
            print(f'ONGRID PDF ERROR: {e}')
            import traceback; traceback.print_exc()

        print('\n--- Generating HYBRID PDF ---')
        hybrid = create_test_hybrid(master, hybrid_tmpl)
        try:
            success, err, pdf_path = generate_pdf_for_proposal(hybrid, master)
            if success and pdf_path:
                dest = os.path.join(output_dir, 'test_hybrid.pdf')
                shutil.copy2(pdf_path, dest)
                print(f'HYBRID PDF saved: {dest}')
            else:
                print(f'HYBRID PDF FAILED: {err}')
        except Exception as e:
            print(f'HYBRID PDF ERROR: {e}')
            import traceback; traceback.print_exc()

        print('\nDone. Check test_pdf_output/ directory.')


if __name__ == '__main__':
    main()
