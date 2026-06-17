from django import template

register = template.Library()

# ==============================
# GET ITEM (dict safe)
# ==============================
@register.filter
def get_item(dictionary, key):
    """
    Acede a valores de um dict com segurança.
    """
    try:
        if isinstance(dictionary, dict):
            return dictionary.get(key)
        return None
    except Exception:
        return None


# ==============================
# GET ATTR (dynamic model field)
# ==============================
@register.filter
def get_attr(obj, attr_name):
    """
    Acede dinamicamente a atributos de objetos Django.
    Ex: mp|get_attr:"av1"
    """
    try:
        if obj is None:
            return ""
        return getattr(obj, attr_name, "")
    except Exception:
        return ""