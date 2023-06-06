# This file is part of the electronic_mail_single module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.pyson import Bool, Eval

__all__ = ['Template']


class Template(metaclass=PoolMeta):
    __name__ = 'electronic.mail.template'

    single_email = fields.Boolean('Single Email',
        help='Check it if you want to send a single email for several records')
    single_report = fields.Boolean('Single Report',
        states={
            'invisible': ~Bool(Eval('single_email')),
        },
        help='Check it if you want to send a single report for several records')

    def group_records(self, records):
        groups = {}
        for r in records:
            if self.eval(getattr(self, 'to'), r) not in groups:
                groups[self.eval(getattr(self, 'to'), r)] = [r]
            else:
                groups[self.eval(getattr(self, 'to'), r)].append(r)
        return [groups[g] for g in groups]
