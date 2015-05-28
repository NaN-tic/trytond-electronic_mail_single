# This file is part of the electronic_mail_single module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from email import Encoders
from email.header import Header
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
import logging
import mimetypes
import threading
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction


__all__ = ['GenerateTemplateEmail']
__metaclass__ = PoolMeta


class GenerateTemplateEmail:
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

    def group_records(self, records):
        start = self.start
        template = start.template
        groups = {}
        for r in records:
            if template.eval(getattr(start, 'to'), r) not in groups:
                groups[template.eval(getattr(start, 'to'), r)] = [r]
            else:
                groups[template.eval(getattr(start, 'to'), r)].append(r)
        return [groups[g] for g in groups]

    def get_attachments(self, ids):
        start = self.start
        template = start.template
        attachments = []
        for report in template.reports:
            report = Pool().get(report.report_name, type='report')
            ext, data, filename, file_name = report.execute(ids, {})

            if file_name:
                filename = template.eval(file_name, ids)
            filename = ext and '%s.%s' % (filename, ext) or filename
            content_type, _ = mimetypes.guess_type(filename)
            maintype, subtype = (
                content_type or 'application/octet-stream'
                ).split('/', 1)

            attachment = MIMEBase(maintype, subtype)
            attachment.set_payload(data)
            Encoders.encode_base64(attachment)
            attachment.add_header(
                'Content-Disposition', 'attachment', filename=filename)
            attachments.append(attachment)
        return attachments

    def render_message(self, record, attachments):
        start = self.start
        template = start.template
        Template = Pool().get('electronic.mail.template')

        message = MIMEMultipart()
        message['date'] = formatdate(localtime=1)

        language = Transaction().context.get('language', 'en_US')
        if template.language:
            language = template.eval(template.language, record)

        with Transaction().set_context(language=language):
            template = Template(template.id)
            message['message_id'] = make_msgid()

            message['from'] = template.eval(start.from_, record)
            message['to'] = template.eval(start.to, record)
            message['cc'] = template.eval(start.cc, record)
            message['subject'] = Header(template.eval(start.subject,
                    record), 'utf-8')

            if template.reply_to:
                eval_result = template.eval(template.reply_to, record)
                if eval_result:
                    message['reply-to'] = eval_result
            if attachments:
                message.set_payload(attachments)

            plain = template.eval(start.plain, record)
            if template.signature:
                User = Pool().get('res.user')
                user = User(Transaction().user)
                if user.signature:
                    signature = user.signature
                    plain = '%s\n--\n%s' % (
                            plain,
                            signature.encode("utf8"),
                            )
            message.attach(MIMEText(plain, _charset='utf-8'))
        return message

    def transition_send(self):
        start = self.start
        template = start.template
        Model = Pool().get(template.model.model)

        records = Model.browse(Transaction().context.get('active_ids'))
        if not template.single_email:
            super(GenerateTemplateEmail, self).transition_send()
        else:
            self.validate_emails()
            for records in self.group_records(records):
                record = records[0]
                attachments = self.get_attachments([r.id for r in records])
                message = self.render_message(record, attachments)
                self.send_email(message, record)
        return 'end'

    def send_email(self, message, record):
        start = self.start
        template = start.template
        company_id = Transaction().context.get('company')
        context = {'company': company_id}
        if start.bcc:
            context['bcc'] = start.bcc
        db_name = Transaction().cursor.dbname
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
            with transaction.set_context(**context):
                email_configuration = EmailConfiguration(1)
            mailbox = email_configuration.outbox

            template = Template(template_id)
            email = Email.create_from_email(message, mailbox, context)

            email.send_email()
            logging.getLogger('Mail').info(
                'Send template email: %s - %s' % (template.name, email.id))

            template.add_event(record, email)
            transaction.cursor.commit()
