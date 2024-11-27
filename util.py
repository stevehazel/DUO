
def dec_format(d):
    return dec_int(d) if d == d.to_integral() else d.normalize()


def dec_int(d):
    from decimal import Decimal
    return d.quantize(Decimal(1))


def emit_state_change(origin, action, details=None):
    # FIXME: use logger for this
    print(f'StateChange: {origin} -> {action} [{details}]')
