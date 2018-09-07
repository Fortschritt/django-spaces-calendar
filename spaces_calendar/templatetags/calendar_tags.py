from django import template
from django.utils.translation import ugettext as _

register = template.Library()

@register.simple_tag
def lookup(obj, *args):
    """
    lookup values in dicts or lists that are arbitrarily nested.
    """
    for arg in args:
        if isinstance(obj, dict):
            obj = obj.get(arg, '')
        elif isinstance(obj, list):
            obj = obj[arg]
        else:
            return ''
    return obj

@register.filter(name="strftime")
def strftime(d, arg):
    return _(d.strftime(arg))

@register.simple_tag
def month_name(month):
    """
    for a give month(int), return the full name.
    """
    months = [
        'January',
        'February',
        'March',
        'April',
        'May',
        'June',
        'July',
        'August',
        'September',
        'October',
        'November',
        'December'
    ]
    return _(months[month-1])

@register.simple_tag
def is_equal_day(day1, year, month, day):
    """
        Compares a datetime with the given year, month and day.Returns true 
        if year, month and day are the same, else False. Hours and finer are 
        ignored.
    """
    return  day1.year == year and \
            day1.month == month and \
            day1.day == day

@register.filter
def is_owner(user, arg):
    """
    Returns True if user and object author are the same account, else False.
    Usage:
    {% user|is_owner:event %}
    """
    return user == arg.calendarevent.author
