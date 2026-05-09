import re
import html
from flask import current_app
from models import Post


def parse_bbcode(text):
    text = re.sub(
        r"\[b\](.*?)\[/b\]",
        r"<strong>\1</strong>",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    text = re.sub(
        r"\[i\](.*?)\[/i\]", r"<em>\1</em>", text, flags=re.IGNORECASE | re.DOTALL
    )
    text = re.sub(
        r"\[u\](.*?)\[/u\]", r"<u>\1</u>", text, flags=re.IGNORECASE | re.DOTALL
    )
    text = re.sub(
        r"\[s\](.*?)\[/s\]", r"<del>\1</del>", text, flags=re.IGNORECASE | re.DOTALL
    )
    text = re.sub(
        r"\[spoiler\](.*?)\[/spoiler\]",
        r'<details class="spoiler"><summary>Спойлер</summary>\1</details>',
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    text = re.sub(
        r"\[code\](.*?)\[/code\]",
        r"<pre><code>\1</code></pre>",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return text


def process_urls(text):
    def magnet_replace(match):
        url = match.group(0)
        return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{url}</a>'

    text = re.sub(r'magnet:\?[^\s<>"\']+', magnet_replace, text, flags=re.IGNORECASE)

    def url_replace(match):
        url = match.group(0)
        if re.search(
            r"^(https?://)?(127\.0\.0\.1|\[::1\]|::1)([/:]|$)", url, re.IGNORECASE
        ):
            if not url.startswith("http://") and not url.startswith("https://"):
                url = "http://" + url
            return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{match.group(0)}</a>'
        if re.search(r"\.(i2p|onion)(/|$)", url, re.IGNORECASE):
            if not url.startswith("http://") and not url.startswith("https://"):
                url = "http://" + url
            return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{match.group(0)}</a>'
        return f'{match.group(0)}<span class="clearnet-warning">ClearNet</span>'

    text = re.sub(
        r"""(?i)\b((?:https?://|ftp://)?[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:[a-z]{2,}|i2p|onion)(?:/[^\s<>"']*)?)\b""",
        url_replace,
        text,
    )
    text = re.sub(
        r"""(?i)\b((?:https?://|ftp://)?(?:[0-9]{1,3}\.){3}[0-9]{1,3})(?::[0-9]+)?(?:/[^\s<>"']*)?\b""",
        url_replace,
        text,
    )
    return text


def process_comment(text, board_name, thread_id):
    text = html.escape(text)
    text = text.replace("&gt;&gt;", ">>")
    text = text.replace("&#91;", "[").replace("&#93;", "]")

    def replace_quote(match):
        num = match.group(1)
        quoted_post = Post.query.filter_by(id=num, thread_id=thread_id).first()
        if quoted_post:
            quote_text = html.escape(quoted_post.comment)
            if len(quote_text) > 200:
                quote_text = quote_text[:200] + "..."
            return f'<blockquote class="inline-quote"><a href="{current_app.url_for("board.thread", board_name=board_name, thread_id=thread_id)}#post{num}">&gt;&gt;{num}</a> {quote_text}</blockquote>'
        return match.group(0)

    text = re.sub(r">>(\d+)", replace_quote, text)
    text = parse_bbcode(text)
    text = process_urls(text)
    return text
