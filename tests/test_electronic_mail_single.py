#!/usr/bin/env python
# This file is part of the electronic_mail_single module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.tests.test_tryton import test_view, test_depends
import trytond.tests.test_tryton
import unittest


class ElectronicMailSingleTestCase(unittest.TestCase):
    'Test Electronic Mail Single module'

    def setUp(self):
        trytond.tests.test_tryton.install_module('electronic_mail_single')

    def test0005views(self):
        'Test views'
        test_view('electronic_mail_single')

    def test0006depends(self):
        'Test depends'
        test_depends()


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        ElectronicMailSingleTestCase))
    return suite
