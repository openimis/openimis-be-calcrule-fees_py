import json

from django.contrib.contenttypes.models import ContentType
from invoice.apps import InvoiceConfig
from invoice.models import Bill
from payer.models import Payer


class BatchRunToBillConverter(object):

    @classmethod
    def to_bill_obj(cls, batch_run, payment_plan, payment):
        bill = {}
        cls.build_subject(batch_run, bill)
        cls.build_thirdparty(bill)
        cls.build_code(payment_plan, payment, batch_run, bill)
        cls.build_date_dates(batch_run, bill)
        #cls.build_tax_analysis(bill)
        cls.build_currency(bill)
        cls.build_status(bill)
        cls.build_terms(payment_plan, bill)
        return bill

    @classmethod
    def build_subject(cls, batch_run, bill):
        bill["subject_id"] = batch_run.id
        bill['subject_type'] = ContentType.objects.get_for_model(batch_run)

    @classmethod
    def build_thirdparty(cls, bill):
        # take default payer
        bill["thirdparty_id"] = 1
        bill['thirdparty_type'] = ContentType.objects.get_for_model(Payer)

    @classmethod
    def build_code(cls, payment_plan, payment, batch_run, bill):
        # take default payer id = 1
        bill["code"] = f"" \
            f"{payment_plan.code}" \
            f"-{payment.code_tp}" \
            f"-1" \
            f"-{batch_run.run_year}" \
            f"-{batch_run.run_month}"

    @classmethod
    def build_date_dates(cls, batch_run, bill):
        from core import datetime, datetimedelta
        bill["date_due"] = batch_run.run_date + datetimedelta(days=30)
        bill["date_bill"] = batch_run.run_date
        bill["date_valid_from"] = batch_run.run_date
        # TODO - explain/clarify meaning of 'validity to' of this field
        #bill["date_valid_to"] = batch_run.expiry_date

    @classmethod
    def build_tax_analysis(cls, bill):
        bill["tax_analysis"] = None

    @classmethod
    def build_currency(cls, bill):
        bill["currency_tp_code"] = InvoiceConfig.default_currency_code
        bill["currency_code"] = InvoiceConfig.default_currency_code

    @classmethod
    def build_status(cls, bill):
        bill["status"] = Bill.Status.VALIDATED.value

    @classmethod
    def build_terms(cls, payment_plan, bill):
        pp_params = payment_plan.json_ext
        if isinstance(pp_params, str):
            pp_params = json.loads(pp_params)
        if pp_params:
            pp_params = pp_params["calculation_rule"] if "calculation_rule" in pp_params else None
        fee_rate = 0
        if "fee_rate" in pp_params:
            fee_rate = int(pp_params["fee_rate"])
        bill["terms"] = f'{payment_plan.benefit_plan.name}, {fee_rate}'

    @classmethod
    def build_amounts(cls, line_item, bill_update):
        bill_update["amount_net"] = line_item["amount_net"]
        bill_update["amount_total"] = line_item["amount_total"]
        bill_update["amount_discount"] = 0 if line_item["discount"] else line_item["discount"]
