# This file is part of the electronic_mail_single module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import unittest
import trytond.tests.test_tryton
from trytond.tests.test_tryton import ModuleTestCase


class ElectronicMailSingleTestCase(ModuleTestCase):
    'Test Electronic Mail Single module'
    module = 'electronic_mail_single'


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        ElectronicMailSingleTestCase))
    return suite