#!/usr/bin/env python3
"""
Seed the master account and default templates.
Usage: python database/seed.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from models.user import User
from models.template import Template
from models.company import CompanySetting
from werkzeug.security import generate_password_hash
import getpass


def seed_company_settings(app):
    """Ensure company settings exist."""
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
        existing = CompanySetting.query.filter_by(key=key).first()
        if not existing:
            db.session.add(CompanySetting(key=key, value=value))
    db.session.commit()
    print('Company settings seeded.')


def seed_master():
    app = create_app()
    with app.app_context():
        db.create_all()
        seed_company_settings(app)

        existing = User.query.filter_by(role='MASTER').first()
        if existing:
            print(f'Master account already exists: {existing.username}')
        else:
            print('=== Create Master Account ===')
            name = input('Master name [Sologix Admin]: ').strip() or 'Sologix Admin'
            username = input('Master username [master]: ').strip() or 'master'
            password = getpass.getpass('Master password: ')
            if not password:
                print('Password cannot be empty.')
                sys.exit(1)
            confirm = getpass.getpass('Confirm password: ')
            if password != confirm:
                print('Passwords do not match.')
                sys.exit(1)

            master = User(
                name=name, username=username,
                password_hash=generate_password_hash(password),
                role='MASTER', is_active=True
            )
            db.session.add(master)
            db.session.flush()

            ongrid = Template(name='Ongrid v1', system_type='ONGRID', version=1,
                              is_active=True, html_file='pdf/ongrid.html', created_by=master.id)
            hybrid = Template(name='Hybrid v1', system_type='HYBRID', version=1,
                              is_active=True, html_file='pdf/hybrid.html', created_by=master.id)
            db.session.add(ongrid)
            db.session.add(hybrid)
            db.session.commit()
            print(f'Master account created: {username}')
            print('Templates seeded: Ongrid v1, Hybrid v1')


if __name__ == '__main__':
    seed_master()
