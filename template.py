# This file is part of the electronic_mail_single module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from email import Encoders
from email.header import Header
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
import mimetypes
from trytond.model import fields
from trytond.pool import Pool, PoolMeta

from trytond.transaction import Transaction


__all__ = ['Template']
__metaclass__ = PoolMeta


class Template:
    __name__ = 'electronic.mail.template'

    single_email = fields.Boolean('Single email',
        help='Check it if you want to send a single email for several records '
            '(the optional attachment will be generated as a single file for '
            'all these records). If you don\'t check it, an email with its '
            'optional attachment will be send for each record.')

    def group_records(self, records):
        groups = {}
        for r in records:
            if self.eval(getattr(self, 'to'), r) not in groups:
                groups[self.eval(getattr(self, 'to'), r)] = [r]
            else:
                groups[self.eval(getattr(self, 'to'), r)].append(r)
        return [groups[g] for g in groups]

    def get_attachments(self, records):
        record_ids = [r.id for r in records]
        attachments = []
        for report in self.reports:
            report = Pool().get(report.report_name, type='report')
            ext, data, filename, file_name = report.execute(record_ids, {})

            if file_name:
                filename = self.eval(file_name, record_ids).decode('utf-8')
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
        message = MIMEMultipart()
        message['date'] = formatdate(localtime=1)

        language = Transaction().context.get('language', 'en_US')
        if self.language:
            language = self.eval(self.language, record)

        with Transaction().set_context(language=language):
            message['message_id'] = make_msgid()

            message['from'] = self.eval(self.from_, record)
            message['to'] = self.eval(self.to, record)
            message['cc'] = self.eval(self.cc, record)
            message['subject'] = Header(self.eval(self.subject, record),
                'utf-8')

            if self.reply_to:
                eval_result = self.eval(self.reply_to, record)
                if eval_result:
                    message['reply-to'] = eval_result
            if attachments:
                message.set_payload(attachments)

            plain = self.eval(self.plain, record)
            if self.signature:
                User = Pool().get('res.user')
                user = User(Transaction().user)
                if user.signature:
                    signature = user.signature
                    plain = '%s\n--\n%s' % (plain, signature.encode("utf8"))
            message.attach(MIMEText(plain, _charset='utf-8'))
        return message
