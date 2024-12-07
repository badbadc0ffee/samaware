from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Return a value from a dict by a variable key.
    Inspired by: https://stackoverflow.com/q/8000022
    """  # noqa: D415

    return dictionary.get(key)


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
