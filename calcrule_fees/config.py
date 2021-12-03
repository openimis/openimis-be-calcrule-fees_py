CLASS_RULE_PARAM_VALIDATION = [
    {
        "class": "PaymentPlan",
        "parameters": [
            {
                "type": "number",
                "name": "fee_rate",
                "label": {
                    "en": "fee rate(%)",
                    "fr": "Taux de frais(%)"
                },
                "rights": {
                    'read': "157101",
                    "write": "157102",
                    "update": "157103",
                    "replace": "157206"
                },
                "relevance": "True",
                "condition": ".$_<100",
                "default": "1.5"
            },
            {
                "type": "string",
                "name": "paymentOrigin",
                "label": {
                    "en": "Payement origin",
                    "fr": "Origine de paiement"
                },
                "rights": {
                    "read": "157101",
                    "write": "157102",
                    "update": "157103",
                    "replace": "157206"
                },
                "relevance": "True",
                "condition": "True",
                "default": ""
            },
        ]
    },
]

FROM_TO = [
        {"from": "BatchRun", "to": "Bill"},
        {"from": "InvoicePayment", "to": "BillItem"}
]

DESCRIPTION_CONTRIBUTION_VALUATION = F"" \
    F"This calculation will, for the selected level and product," \
    F" calculate how much the insurance need to" \
    F" pay the payment platform for the fee for payment service"
