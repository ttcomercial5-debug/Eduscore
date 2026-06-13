from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Retorna item de um dict de forma segura.
    Evita erro caso venha string ou None.
    """
    try:
        if isinstance(dictionary, dict):
            return dictionary.get(key)
        return None
    except Exception:
        return None