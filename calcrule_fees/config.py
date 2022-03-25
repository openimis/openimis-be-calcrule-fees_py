CLASS_RULE_PARAM_VALIDATION = [
    {
        "class": "PaymentPlan",
        "parameters": [
            {
                "type": "number",
                "name": "fee_rate",
                "label": {
                    "en": "Fee rate(%)",
                    "fr": "Taux de frais(%)"
                },
                "rights": {
                    'read': "157101",
                    "write": "157102",
                    "update": "157103",
                    "replace": "157206"
                },
                "relevance": "True",
                "condition": "INPUT<100",
                "default": "2"
            },
            {
                "type": "string",
                "name": "payment_origin",
                "label": {
                    "en": "Payment origin",
                    "fr": "Origine de paiement"
                },
                "rights": {
                    "read": "157101",
                    "write": "157102",
                    "update": "157103",
                    "replace": "157206"
                },
                "relevance": "True",
                "default": "value"
            },
        ]
    },
    {
        "class": "Product",
        "parameters": [
            ]
    }
]

FROM_TO = [
        {"from": "BatchRun", "to": "Bill"},
        {"from": "InvoicePayment", "to": "BillItem"}
]

DESCRIPTION_CONTRIBUTION_VALUATION = F"" \
    F"This calculation will, for the selected level and product," \
    F" calculate how much the insurance need to" \
    F" pay the payment platform for the fee for payment service"
