"""
Custom template tags for orders app.
Provides num_to_words filter for Russian currency amount in words.
"""
from django import template

register = template.Library()


def _hundreds(n: int, male: bool = True) -> str:
    """Convert 0–999 to Russian words."""
    h_words = ['', 'сто', 'двести', 'триста', 'четыреста',
               'пятьсот', 'шестьсот', 'семьсот', 'восемьсот', 'девятьсот']
    t_words = ['', 'десять', 'двадцать', 'тридцать', 'сорок',
               'пятьдесят', 'шестьдесят', 'семьдесят', 'восемьдесят', 'девяносто']
    u_male   = ['', 'один', 'два', 'три', 'четыре', 'пять',
                'шесть', 'семь', 'восемь', 'девять']
    u_female = ['', 'одна', 'две', 'три', 'четыре', 'пять',
                'шесть', 'семь', 'восемь', 'девять']
    teens    = ['десять', 'одиннадцать', 'двенадцать', 'тринадцать',
                'четырнадцать', 'пятнадцать', 'шестнадцать', 'семнадцать',
                'восемнадцать', 'девятнадцать']

    parts = []
    h = n // 100
    t = (n % 100) // 10
    u = n % 10

    if h:
        parts.append(h_words[h])
    if t == 1:
        parts.append(teens[u])
        u = 0
    elif t:
        parts.append(t_words[t])

    if u:
        parts.append((u_male if male else u_female)[u])

    return ' '.join(parts)


def _plural(n: int, one: str, two: str, five: str) -> str:
    """Russian plural form."""
    n = abs(n) % 100
    if 11 <= n <= 19:
        return five
    r = n % 10
    if r == 1:
        return one
    if 2 <= r <= 4:
        return two
    return five


def amount_in_words(amount, currency_name='сом') -> str:
    """
    Convert a numeric amount to Russian words.
    Example: 10020.50 → «Десять тысяч двадцать сом 50 тиин»
    """
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return ''

    rubles  = int(amount)
    kopecks = round((amount - rubles) * 100)

    parts = []

    billions = rubles // 1_000_000_000
    if billions:
        parts.append(_hundreds(billions, male=True))
        parts.append(_plural(billions, 'миллиард', 'миллиарда', 'миллиардов'))
        rubles %= 1_000_000_000

    millions = rubles // 1_000_000
    if millions:
        parts.append(_hundreds(millions, male=True))
        parts.append(_plural(millions, 'миллион', 'миллиона', 'миллионов'))
        rubles %= 1_000_000

    thousands = rubles // 1_000
    if thousands:
        parts.append(_hundreds(thousands, male=False))
        parts.append(_plural(thousands, 'тысяча', 'тысячи', 'тысяч'))
        rubles %= 1_000

    if rubles or not parts:
        parts.append(_hundreds(rubles, male=True))

    result = ' '.join(p for p in parts if p).strip()
    if result:
        result = result[0].upper() + result[1:]

    # Currency
    int_amount = int(amount)
    result += f' {_plural(int_amount, currency_name, currency_name, currency_name)}'

    # Kopecks / tiin
    result += f' {kopecks:02d} тиин'

    return result


@register.filter(name='num_to_words')
def num_to_words(value, currency='сом'):
    """Template filter: {{ order.total_price|num_to_words:'сом' }}"""
    return amount_in_words(value, currency)
