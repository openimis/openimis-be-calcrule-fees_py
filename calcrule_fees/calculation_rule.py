import json

from calcrule_fees.apps import AbsCalculationRule
from calcrule_fees.config import CLASS_RULE_PARAM_VALIDATION, \
    DESCRIPTION_CONTRIBUTION_VALUATION, FROM_TO
from calcrule_fees.converters import \
    BatchRunToBillConverter, InvoicePaymentToBillItemConverter
from django.core.exceptions import ValidationError
from gettext import gettext as _
from invoice.models import InvoicePayment
from invoice.services import BillService
from core.signals import *
from core import datetime
from django.contrib.contenttypes.models import ContentType
from contribution.models import Premium
from contribution_plan.models import PaymentPlan
from product.models import Product
from claim_batch.models import BatchRun
from core.models import User


class FeesCalculationRule(AbsCalculationRule):
    version = 1
    uuid = "1a69f129-afa3-4919-a53d-e111f5fb2b2b"
    calculation_rule_name = "payment: fees"
    description = DESCRIPTION_CONTRIBUTION_VALUATION
    impacted_class_parameter = CLASS_RULE_PARAM_VALIDATION
    date_valid_from = datetime.datetime(2000, 1, 1)
    date_valid_to = None
    status = "active"
    from_to = FROM_TO
    type = "account_payable"
    sub_type = "fees"

    signal_get_rule_name = Signal(providing_args=[])
    signal_get_rule_details = Signal(providing_args=[])
    signal_get_param = Signal(providing_args=[])
    signal_get_linked_class = Signal(providing_args=[])
    signal_calculate_event = Signal(providing_args=[])
    signal_convert_from_to = Signal(providing_args=[])

    @classmethod
    def ready(cls):
        now = datetime.datetime.now()
        condition_is_valid = (now >= cls.date_valid_from and now <= cls.date_valid_to) \
            if cls.date_valid_to else (now >= cls.date_valid_from and cls.date_valid_to is None)
        if condition_is_valid:
            if cls.status == "active":
                # register signals getParameter to getParameter signal and getLinkedClass ot getLinkedClass signal
                cls.signal_get_rule_name.connect(cls.get_rule_name, dispatch_uid="on_get_rule_name_signal")
                cls.signal_get_rule_details.connect(cls.get_rule_details, dispatch_uid="on_get_rule_details_signal")
                cls.signal_get_param.connect(cls.get_parameters, dispatch_uid="on_get_param_signal")
                cls.signal_get_linked_class.connect(cls.get_linked_class, dispatch_uid="on_get_linked_class_signal")
                cls.signal_calculate_event.connect(cls.run_calculation_rules, dispatch_uid="on_calculate_event_signal")
                cls.signal_convert_from_to.connect(cls.run_convert, dispatch_uid="on_convert_from_to")

    @classmethod
    def active_for_object(cls, instance, context, type="account_payable", sub_type="fees"):
        return instance.__class__.__name__ == "PaymentPlan" \
               and context in ["BatchPayment"] \
               and cls.check_calculation(instance)

    @classmethod
    def check_calculation(cls, instance):
        class_name = instance.__class__.__name__
        match = False
        if class_name == "ABCMeta":
            match = str(cls.uuid) == str(instance.uuid)
        elif class_name == "PaymentPlan":
            match = cls.uuid == str(instance.calculation)
        elif class_name == "BatchRun":
            # BatchRun → Product or Location if no prodcut
            match = cls.check_calculation(instance.location)
        elif class_name == "Location":
            #  location → ProductS (Product also related to Region if the location is a district)
            if instance.type in ["D", "R"]:
                products = Product.objects.filter(location=instance, validity_to__isnull=True)
                for product in products:
                    if cls.check_calculation(product):
                        match = True
                        break
        elif class_name == "Product":
            # if product → paymentPlans
            payment_plans = PaymentPlan.objects.filter(benefit_plan=instance, is_deleted=False)
            for pp in payment_plans:
                if cls.check_calculation(pp):
                    match = True
                    break
        return match

    @classmethod
    def calculate(cls, instance, **kwargs):
        context = kwargs.get('context', None)
        if instance.__class__.__name__ == "Premium":
            if context == "BatchPayment":
                return cls._calculate_fee(instance, **kwargs)
        if instance.__class__.__name__ == "PaymentPlan":
            if context == "BatchPayment":
                return cls._calculate_batch_payment(instance, **kwargs)
        elif context == "BatchValuation":
            pass
        elif context == "IndividualPayment":
            pass
        elif context == "IndividualValuation":
            pass

    @classmethod
    def get_linked_class(cls, sender, class_name, **kwargs):
        list_class = []
        if class_name != None:
            model_class = ContentType.objects.filter(model=class_name).first()
            if model_class:
                model_class = model_class.model_class()
                list_class = list_class + \
                             [f.remote_field.model.__name__ for f in model_class._meta.fields
                              if f.get_internal_type() == 'ForeignKey' and f.remote_field.model.__name__ != "User"]
        else:
            list_class.append("Calculation")
        # because we have calculation in PaymentPlan
        #  as uuid - we have to consider this case
        if class_name == "PaymentPlan":
            list_class.append("Calculation")
        return list_class

    @classmethod
    def convert(cls, instance, convert_to, **kwargs):
        results = {}
        context = kwargs.get('context', None)
        if context == 'BatchPayment':
            payment = kwargs.get('payment', None)
            payment_plan = kwargs.get('payment_plan', None)
            convert_from = instance.__class__.__name__
            if convert_from == "BatchRun":
                results = cls._convert_fees(instance, payment, payment_plan)
            results['user'] = kwargs.get('user', None)
            BillService.bill_create(convert_results=results)
        return results

    @classmethod
    def _get_batch_run_parameters(cls, **kwargs):
        audit_user_id = kwargs.get('audit_user_id', None)
        product_id = kwargs.get('product_id', None)
        start_date = kwargs.get('start_date', None)
        end_date = kwargs.get('end_date', None)
        work_data = kwargs.get('work_data', None)
        if work_data:
            batch_run = work_data['created_run']
        else:
            batch_run = None
        return audit_user_id, product_id, start_date, end_date, batch_run, work_data
    
    @classmethod
    def _calculate_fee(cls, instance, **kwargs):
        payment_plan = kwargs.get('payment_plan', None)
        if payment_plan:
            pp_params = payment_plan.json_ext
            if isinstance(pp_params, str):
                pp_params = json.loads(pp_params)
            if pp_params:
                pp_params = pp_params["calculation_rule"] if "calculation_rule" in pp_params else None
            fee_rate = 0
            if "fee_rate" in pp_params:
                fee_rate = float(pp_params["fee_rate"])
            return float(instance.amount) * (fee_rate / 100)
        else:
            return 0
    
    @classmethod
    def _calculate_batch_payment(cls, instance, **kwargs):
        context = kwargs.get('context', None)
        audit_user_id, product_id, start_date, end_date, batch_run, work_data = \
            cls._get_batch_run_parameters(**kwargs)

        # if this is trigerred by batch_run - take user data from audit_user_id
        user = User.objects.filter(i_user__id=audit_user_id).first()
        if user is None:
            raise ValidationError(_("Such User does not exist"))
        
        product = work_data['product']

        # take all payments related to particular invoice per product
        payments_to_process = []
        invoice_payments = InvoicePayment.objects.filter(
            invoice__line_items__line_id__isnull=False, is_deleted=False,
            date_created__gte=start_date, date_created__lte=end_date
        )
        # select payments to be processed
        for ip in invoice_payments:
            invoice = ip.invoice
            contributions = None
            for line_item in invoice.line_items.all():
                if line_item.line_type.name == 'policy':
                    if line_item.line.product.id == product.id:
                        payments_to_process.append(ip)
                if line_item.line_type.name == 'contract contribution plan details':
                    if line_item.line.contribution_plan.benefit_plan.id == product.id:
                        payments_to_process.append(ip)
        for payment in payments_to_process:
            cls.run_convert(
                instance=batch_run,
                convert_to='Bill',
                payment=payment,
                user=user,
                payment_plan=instance,
                context=context
            )

        return "conversion finished 'fees'"

    @classmethod
    def _convert_fees(cls, instance, invoice_payment, payment_plan):
        bill = BatchRunToBillConverter.to_bill_obj(
            batch_run=instance,
            payment_plan=payment_plan,
            payment=invoice_payment
        )
        bill_line_items = []
        # collect contributions
        contributions = []
        invoice = invoice_payment.invoice
        for line_item in invoice.line_items.all():
            line = line_item.line
            line_type_name = line_item.line_type.name
            if line_type_name == 'policy':
                for p in line.premiums.all():
                    contributions.append(p)
            if line_type_name == 'contract contribution plan details':
                contributions.append(line.contribution)

        for premium in contributions:
            fee_value = cls.calculate(instance=premium, payment_plan=payment_plan, context='BatchPayment')
            bill_line_item = InvoicePaymentToBillItemConverter.to_bill_line_item_obj(
                premium=premium,
                batch_run=instance,
                payment_plan=payment_plan,
                fee_value=fee_value
            )
            bill_line_items.append(bill_line_item)

        return {
            'bill_data': bill,
            'bill_data_line': bill_line_items,
            'type_conversion': 'batch run invoice payment - bill'
        }
