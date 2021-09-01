# This file is part of the electronic_mail_single module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from . import template
from . import electronic_mail_wizard


def register():
    Pool.register(
        template.Template,
        electronic_mail_wizard.TemplateEmailStart,
        module='electronic_mail_single', type_='model')
    Pool.register(
        electronic_mail_wizard.GenerateTemplateEmail,
        module='electronic_mail_single', type_='wizard')
