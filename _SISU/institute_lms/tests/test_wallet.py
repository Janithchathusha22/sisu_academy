import unittest
from institute_lms.wallet_rules import minor,reserve,transition,payout_details,class_quote,csv_cell

class WalletRules(unittest.TestCase):
    def test_money_is_exact_and_bounded(self):
        self.assertEqual(minor('10.01'),1001)
        for value in ('NaN','Infinity','-1','0.001','10000000'):
            with self.assertRaises(ValueError):minor(value)
    def test_reservation_prevents_reusing_available_funds(self):
        a,h=reserve(3000,0,2000,2000)
        self.assertEqual((a,h),(1000,2000))
        with self.assertRaises(ValueError):reserve(a,h,2000,2000)
    def test_minimum_exact_boundary(self):
        with self.assertRaises(ValueError):reserve(9000,0,1999,2000)
        self.assertEqual(reserve(2000,0,2000,2000),(0,2000))
    def test_completion_and_rejection_conserve_funds(self):
        self.assertEqual(transition('Pending','Processing',2000),(0,0))
        self.assertEqual(transition('Processing','Completed',2000,reference='BANK-01'),(0,-2000))
        self.assertEqual(transition('Pending','Rejected',2000,reason='Wrong bank'),(2000,-2000))
        self.assertEqual(transition('Processing','Rejected',2000,reason='Transfer cancelled'),(2000,-2000))
    def test_terminal_requests_cannot_be_replayed_as_new_transitions(self):
        for old,new in [('Pending','Completed'),('Completed','Rejected'),('Rejected','Processing')]:
            with self.assertRaises(ValueError):transition(old,new,2000,'REF','Reason')
        with self.assertRaises(ValueError):transition('Processing','Completed',2000)
        with self.assertRaises(ValueError):transition('Pending','Rejected',2000)
    def test_region_and_bank_fields_are_validated(self):
        local={'kind':'Local Bank','country':'Sri Lanka','bank':'Demo Bank','branch':'001','holder':'Test Name','account':'00000123'}
        self.assertEqual(payout_details(local)['account'],'00000123')
        with self.assertRaises(ValueError):payout_details({**local,'country':'United Kingdom'})
        with self.assertRaises(ValueError):payout_details({**local,'account':''})
    def test_international_methods_and_iban_checksum(self):
        self.assertEqual(payout_details({'kind':'Wise','country':'France','email':'test@example.invalid'})['kind'],'Wise')
        swift={'kind':'SWIFT / IBAN','country':'United Kingdom','bank':'Demo','holder':'Test','swift':'NWBKGB2L','iban':'GB82 WEST 1234 5698 7654 32'}
        self.assertEqual(payout_details(swift)['iban'],'GB82WEST12345698765432')
        with self.assertRaises(ValueError):payout_details({**swift,'iban':'GB81WEST12345698765432'})
    def test_platform_fee_is_separate_and_school_is_exempt(self):
        self.assertEqual(class_quote(1000),{'class_minor':1000,'platform_minor':100,'total_minor':1100})
        self.assertEqual(class_quote(0)['total_minor'],100)
        self.assertEqual(class_quote(1000,school=True)['total_minor'],0)
    def test_spreadsheet_formula_injection_is_neutralized(self):
        for value in ('=cmd()','+sum(1)','@lookup()',' -1','\t=1'):
            self.assertTrue(csv_cell(value).startswith("'"))
        self.assertEqual(csv_cell('Bank\r\nName'),'Bank  Name')
