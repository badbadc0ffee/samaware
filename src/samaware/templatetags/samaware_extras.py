from django import template

register = template.Library()


@register.filter
def count_class(value):
    """
    Returns the Pretalx/Bootstrap CSS class suffix (such as "success") for cases where the class should be
    determined by a count of 0 being OK and other values being undesirable.
    """

    if int(value) == 0:
        return 'success'
    else:
        return 'warning'
