"""
Words that name a deposit or a prepayment in the languages the payment line
speaks (stems where a word declines), lower case. A sentence of the
assistant's own words that holds one is about the deposit.
"""

DEPOSIT_TERMS: tuple[str, ...] = (
    # en
    "deposit",
    "prepay",
    "pre-pay",
    "down payment",
    # ru, uk, kk
    "депозит",
    "предоплат",
    "залог",
    "аванс",
    "передоплат",
    "завдат",
    "алдын ала төлем",
    # ka
    "დეპოზიტ",
    "წინასწარ გადახდ",
    "ავანს",
    # hy
    "կանխավճար",
    "դեպոզիտ",
    # az, tr
    "depozit",
    "ilkin ödəniş",
    "kapora",
    "ön ödeme",
    # he, ar
    "פיקדון",
    "מקדמה",
    "عربون",
    "دفعة مقدمة",
    # de
    "anzahlung",
    "kaution",
    "vorauszahlung",
    # fr, es, it, pt
    "acompte",
    "arrhes",
    "dépôt",
    "depósito",
    "anticipo",
    "señal",
    "acconto",
    "caparra",
    "sinal",
    "caução",
    # pl
    "zaliczk",
    "zadat",
    "depozyt",
    "przedpłat",
)
