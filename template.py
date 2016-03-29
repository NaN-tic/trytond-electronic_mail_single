# This file is part of the electronic_mail_single module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from trytond.model import fields
from trytond.pool import Pool, PoolMeta

from trytond.transaction import Transaction


__all__ = ['Template']


class Template:
    __metaclass__ = PoolMeta
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
