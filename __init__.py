# This file is part of the electronic_mail_single module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from .template import *
from .electronic_mail_wizard import *


def register():
    Pool.register(
        Template,
        module='electronic_mail_single', type_='model')
    Pool.register(
        GenerateTemplateEmail,
        module='electronic_mail_single', type_='wizard')
