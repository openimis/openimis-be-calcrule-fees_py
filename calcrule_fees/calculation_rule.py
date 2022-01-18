from calcrule_fees.apps import AbsCalculationRule
from calcrule_fees.config import CLASS_RULE_PARAM_VALIDATION, \
    DESCRIPTION_CONTRIBUTION_VALUATION, FROM_TO
from django.core.exceptions import ValidationError
from gettext import gettext as _
from invoice.services import BillService
from core.signals import *
from core import datetime
from django.contrib.contenttypes.models import ContentType
from contribution_plan.models import PaymentPlan
from product.models import Product


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
    sub_type = "third_party_payment"

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
    def active_for_object(cls, instance, context, type, sub_type):
        return instance.__class__.__name__ == "PaymentPlan" \
               and context in ["BatchPayment"] \
               and cls.check_calculation(instance)

    @classmethod
    def check_calculation(cls, instance):
        class_name = instance.__class__.__name__
        match = False
        if class_name == "PaymentPlan":
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
        if instance.__class__.__name__ == "Contribution":
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
        pass
