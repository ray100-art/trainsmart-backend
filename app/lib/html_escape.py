import html


def esc(value: str) -> str:
    return html.escape(str(value), quote=True)
