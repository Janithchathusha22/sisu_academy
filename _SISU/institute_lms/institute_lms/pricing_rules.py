"""Currency-safe contract mathematics. Amounts are integer minor units, never floats."""
PRODUCTS = ('Platform', 'Class payment', 'AI Papers', 'Study Space', 'To-do', 'Journal')
CURRENCIES = ('USD', 'LKR', 'EUR', 'GBP', 'AED', 'SAR')

def integer(value, label, maximum=2000000000):
    if isinstance(value, bool) or not str(value).isascii() or not str(value).isdigit():
        raise ValueError(label + ' must be a nonnegative integer')
    n = int(value)
    if n > maximum: raise ValueError(label + ' is too large')
    return n

def calculate(base_minor, included_units, unit_minor, units, discount_bps=0, tax_bps=0):
    base = integer(base_minor, 'Base amount')
    included = integer(included_units, 'Included units', 10000000)
    rate = integer(unit_minor, 'Unit amount')
    usage = integer(units, 'Usage', 10000000)
    discount = integer(discount_bps, 'Discount', 10000)
    tax = integer(tax_bps, 'Tax', 10000)
    additional = max(0, usage - included)
    subtotal = integer(base + additional * rate, 'Subtotal')
    # Half-up rounding, calculated once on the subtotal, then tax on the net.
    discount_amount = (subtotal * discount + 5000) // 10000
    net = subtotal - discount_amount
    tax_amount = (net * tax + 5000) // 10000
    total = integer(net + tax_amount, 'Total')
    return dict(base_minor=base, units=usage, included_units=included, additional_units=additional,
                unit_minor=rate, subtotal_minor=subtotal, discount_minor=discount_amount,
                tax_minor=tax_amount, total_minor=total)
