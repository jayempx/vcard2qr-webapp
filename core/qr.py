"""PNG and vector SVG share exact module geometry and readability checks."""

import io
import re

from PIL import Image, ImageDraw
import qrcode


def appearance_settings(raw):
    if not isinstance(raw, dict):
        raise ValueError("Appearance must be an object.")
    value = {
        "size": 512,
        "foreground": "#1f3685",
        "background": "#ffffff",
        "transparent": False,
        "rounded": False,
    }
    value.update({k: raw[k] for k in value if k in raw})
    if type(value["size"]) is not int or not 128 <= value["size"] <= 2048:
        raise ValueError("Choose a size between 128 and 2048 pixels.")
    for key in ("foreground", "background"):
        if not isinstance(value[key], str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", value[key]):
            raise ValueError("Use six-digit hexadecimal colors.")
    if any(type(value[k]) is not bool for k in ("transparent", "rounded")):
        raise ValueError("Use on/off values for transparency and rounded modules.")

    def light(color):
        channels = [int(color[n : n + 2], 16) / 255 for n in (1, 3, 5)]
        return sum(
            w * (c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
            for c, w in zip(channels, (0.2126, 0.7152, 0.0722), strict=True)
        )

    foreground = light(value["foreground"])
    background = light("#ffffff" if value["transparent"] else value["background"])
    if foreground >= background or (background + 0.05) / (foreground + 0.05) < 4.5:
        raise ValueError("Use dark modules on a light background, with contrast of at least 4.5:1.")
    return value


def render_export(payload, appearance, format):
    if format not in ("png", "svg"):
        raise ValueError("Choose PNG or SVG.")
    opts = appearance_settings(appearance)
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_Q, border=4)
    try:
        qr.add_data(payload)
        qr.make(fit=True)
    except ValueError, qrcode.exceptions.DataOverflowError:
        raise ValueError("Content exceeds QR capacity. Shorten the content.") from None
    matrix = qr.get_matrix()
    n, size = len(matrix), opts["size"]
    module = size // n
    if module < 3:
        raise ValueError(f"Increase image size to at least {n * 3} pixels for this content.")
    offset = (size - n * module) // 2
    image = (
        Image.new("RGBA", (size, size), (0, 0, 0, 0) if opts["transparent"] else opts["background"])
        if format == "png"
        else None
    )
    draw = ImageDraw.Draw(image) if image else None
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
    ]
    if not opts["transparent"]:
        svg.append(f'<path fill="{opts["background"]}" d="M0 0h{size}v{size}H0z"/>')
    for row, cells in enumerate(matrix):
        for col, cell in enumerate(cells):
            if not cell:
                continue
            x, y = offset + col * module, offset + row * module
            finder = (row < 12 and col < 12) or (row < 12 and col >= n - 12) or (row >= n - 12 and col < 12)
            radius = module // 4 if opts["rounded"] and not finder else 0
            if draw:
                draw.rounded_rectangle(
                    (x, y, x + module - 1, y + module - 1), radius=radius, fill=opts["foreground"]
                )
            else:
                svg.append(
                    f'<rect x="{x}" y="{y}" width="{module}" height="{module}" rx="{radius}" fill="{opts["foreground"]}"/>'
                )
    if image:
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()
    return ("".join(svg) + "</svg>").encode()
