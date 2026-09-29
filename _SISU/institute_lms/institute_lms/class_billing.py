"""Freeze beneficiary and platform fees before an invoice starts checkout."""
from decimal import Decimal
import frappe
from .wallet_rules import minor

def settlement_filters(institute,room=None):
    """Ownership, never the assigned teacher, chooses the tuition beneficiary."""
    filters={'institute':institute.name,'currency':'LKR','enabled':1}
    if room and room.get('owner_type')=='Teacher':
        if not room.get('owner_user'):raise ValueError('Independent classroom owner is missing')
        filters.update(beneficiary='Teacher',owner_user=room.get('owner_user'))
    else:filters['beneficiary']='Institute'
    return filters

def invoice_split(institute,class_amount,student_user=None,room=None):
    if institute.get('school_mode') and (not room or room.get('owner_type')!='Teacher'):return None
    from .owner_pricing import current,amount
    if not student_user:frappe.throw('A student price assignment is required')
    contract=current(student_user,'Class payment')
    if contract.currency!='LKR' or contract.period!='Per payment':frappe.throw('This classroom requires an LKR per-payment assignment')
    wallets=frappe.get_all('IL Wallet',filters=settlement_filters(institute,room),pluck='name',limit_page_length=2)
    if len(wallets)!=1:frappe.throw('Finance must configure exactly one settlement wallet for the classroom owner')
    fee=amount(contract)['total_minor'];earned=minor(class_amount)
    return {'amount':Decimal(earned+fee)/100,'currency':'LKR','payout_wallet':wallets[0],'beneficiary_minor':earned,'platform_minor':fee,'pricing_assignment':contract.name}
