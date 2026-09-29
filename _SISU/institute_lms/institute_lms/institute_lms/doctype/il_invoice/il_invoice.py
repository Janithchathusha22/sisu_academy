import frappe
from frappe.model.document import Document


class ILInvoice(Document):
    def validate(self):
        previous = self.get_doc_before_save()
        if previous and previous.get('payout_wallet'):
            # The recipient and split are frozen before sending the invoice to a
            # gateway. A later membership change must never redirect its revenue.
            for field in ('payout_wallet', 'currency', 'beneficiary_minor',
                          'platform_minor', 'amount', 'institute', 'student',
                          'classroom', 'enrollment'):
                if self.get(field) != previous.get(field):
                    frappe.throw('Invoice financial identity is frozen. Void and reissue an unpaid invoice instead.')
