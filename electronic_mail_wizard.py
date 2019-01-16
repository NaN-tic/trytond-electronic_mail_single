# This file is part of the electronic_mail_single module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import logging
import threading
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction

__all__ = ['GenerateTemplateEmail']

logger = logging.getLogger(__name__)


class GenerateTemplateEmail(metaclass=PoolMeta):
    __name__ = "electronic_mail_wizard.templateemail"

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
        start = self.start
        template = start.template
        Model = Pool().get(template.model.model)

        records = Model.browse(Transaction().context.get('active_ids'))
        if not template.single_email:
            super(GenerateTemplateEmail, self).transition_send()
        else:
            self.validate_emails()
            for records in template.group_records(records):
                record = records[0]
                attachments = template.get_attachments(records)
                message = template.render_message(record, attachments)
                self.send_email(message, record)
        return 'end'

    def send_email(self, message, record):
        start = self.start
        template = start.template
        company_id = Transaction().context.get('company')
        context = {'company': company_id}
        if start.bcc:
            context['bcc'] = start.bcc
        db_name = Transaction().database.name
        uid = Transaction().user
        thread1 = threading.Thread(target=self.send_email_thread,
            args=(db_name, uid, message, record, template.id, context))
        thread1.start()

    def send_email_thread(self, db_name, uid, message, record, template_id,
            context):
        with Transaction().start(db_name, uid) as transaction:
            pool = Pool()
            Email = pool.get('electronic.mail')
            Template = pool.get('electronic.mail.template')
            EmailConfiguration = pool.get('electronic.mail.configuration')

            email_configuration = EmailConfiguration(1)
            mailbox = email_configuration.outbox

            template = Template(template_id)
            email = Email.create_from_email(message, mailbox, context)

            if email:
                email.send_email()
                logger.info('Send template email: %s - %s' % (
                    template.name, email.id))

                Template.add_activities([{
                    'record': record,
                    'template': template,
                    'mail': email,
                    }])  # add activities

                transaction.commit()
