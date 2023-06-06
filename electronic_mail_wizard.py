# This file is part of the electronic_mail_single module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import mimetypes
from email import encoders
from email.mime.base import MIMEBase
from trytond.config import config
from trytond.pool import Pool, PoolMeta
from trytond.model import fields
from trytond.pyson import Eval
from trytond.transaction import Transaction
from trytond.modules.electronic_mail_template.tools import unaccent

__all__ = ['TemplateEmailStart', 'GenerateTemplateEmail']

QUEUE_NAME = config.get('electronic_mail', 'queue_name', default='default')


class TemplateEmailStart(metaclass=PoolMeta):
    __name__ = 'electronic.mail.wizard.templateemail.start'
    mail_single = fields.Boolean('Mail Single', readonly=True)
    report_single = fields.Boolean('Report Single', readonly=True)

    @classmethod
    def __setup__(cls):
        super(TemplateEmailStart, cls).__setup__()
        # disable edit fields when is mail single
        for field in ('from_', 'sender', 'to', 'cc', 'bcc', 'use_tmpl_fields'):
            field_ = getattr(cls, field)
            if field_.states.get('readonly'):
                field_.states['readonly'] |= Eval('mail_single')
            else:
                field_.states['readonly'] = Eval('mail_single')
            field_.depends.add('mail_single')


class GenerateTemplateEmail(metaclass=PoolMeta):
    __name__ = "electronic_mail_wizard.templateemail"

    def default_start(self, fields):
        Template = Pool().get('electronic.mail.template')

        default = super(GenerateTemplateEmail, self).default_start(fields)
        template_id = default.get('template')
        if template_id:
            template = Template(template_id)
            default['mail_single'] = template.single_email
            default['report_single'] = template.single_report
            if template.single_email:
                default['use_tmpl_fields'] = True
        return default

    def validate_emails(self):
        pool = Pool()
        Mail = pool.get('electronic.mail')
        start = self.start
        template = start.template
        Model = pool.get(template.model.model)

        records = Model.browse(Transaction().context.get('active_ids'))
        email_fields = ('to', 'from_', 'cc', 'bcc')
        emails = set()
        for record in records:
            for field in start._fields:
                if field in email_fields and getattr(start, field, False):
                    emails.update(
                        template.eval(getattr(start, field), record).split(',')
                        )
        Mail.validate_emails(emails)

    def transition_send(self):
        pool = Pool()
        Configuration = pool.get('electronic.mail.configuration')
        ElectronicEmail = pool.get('electronic.mail')
        Template = pool.get('electronic.mail.template')

        config = Configuration(1)

        context = Transaction().context
        active_ids = context.get('active_ids', [])
        if not active_ids:
            return 'end'

        start = self.start
        template = start.template
        Model = Pool().get(template.model.model)

        records = Model.browse(active_ids)
        if not template.single_email:
            super(GenerateTemplateEmail, self).transition_send()
        else:
            self.validate_emails()
            for records in template.group_records(records):
                record = records[0]

                # load data in language when send a record
                if template.language:
                    language = template.eval(template.language, record)
                    with Transaction().set_context(language=language):
                        template = Template(template.id)

                values = {'template': template}
                tmpl_fields = ('from_', 'sender', 'to', 'cc', 'bcc', 'subject',
                    'message_id', 'in_reply_to', 'plain', 'html')
                for field_name in tmpl_fields:
                    values[field_name] = getattr(template, field_name)

                message = Template.render(template, record, values,
                    render_report=False)

                # Attach reports
                if template.reports:
                    reports = []
                    if template.single_report:
                        reports += Template.render_reports(template, records)
                    else:
                        for record in records:
                            reports += Template.render_reports(template, record)

                    for report in reports:
                        ext, data, filename, file_name = report[0:5]
                        if file_name:
                            filename = template.eval(file_name, record)
                        filename = unaccent(filename)
                        filename = (ext and '%s.%s' % (filename, ext) or
                            filename)
                        content_type, _ = mimetypes.guess_type(filename)
                        maintype, subtype = (
                            content_type or 'application/octet-stream'
                            ).split('/', 1)

                        attachment = MIMEBase(maintype, subtype)
                        attachment.set_payload(data)
                        encoders.encode_base64(attachment)
                        attachment.add_header(
                            'Content-Disposition', 'attachment',
                            filename=filename)
                        message.attach(attachment)

                electronic_mail = ElectronicEmail.create_from_mail(message,
                    template.mailbox.id)
                if not electronic_mail:
                    continue
                electronic_mail.template = template
                electronic_mail.save()

                with Transaction().set_context(
                        queue_name=QUEUE_NAME,
                        queue_scheduled_at=config.send_email_after):
                    ElectronicEmail.__queue__.send_mail([electronic_mail])

        return 'end'
