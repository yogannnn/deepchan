import html
import os
from datetime import datetime, timezone

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from utils import (
    apply_word_filters,
    check_ban,
    check_rate_limit,
    generate_tripcode,
    get_file_hash,
    get_media_duration,
    process_comment,
    save_files,
)

from core.i18n import t
from forms import PostForm
from models import (
    Board,
    Post,
    PostFile,
    PostFTS,
    RadioTrack,
    Report,
    Thread,
    check_password,
    db,
    get_last_replies,
    hash_password,
)
from services.boards import get_boards, get_visible_board_ids
from services.captcha import generate_captcha, verify_captcha

board_bp = Blueprint("board", __name__, url_prefix="")


def csrf_protect(action):
    from functools import wraps

    from flask import abort, request
    from utils import verify_csrf_token

    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if request.method == "POST":
                user_id = (
                    request.authorization.username
                    if request.authorization
                    else "anonymous"
                )
                token = request.form.get("csrf_token")
                timestamp = request.form.get("csrf_timestamp")
                if not token or not timestamp:
                    abort(403, description="CSRF token missing")
                if not verify_csrf_token(
                    user_id, action, token, timestamp, current_app.config["SECRET_KEY"]
                ):
                    abort(403, description="CSRF token invalid")
            return f(*args, **kwargs)

        return decorated

    return decorator


@board_bp.route("/<string:board_name>/", strict_slashes=False)
def board(board_name):
    board = Board.query.filter_by(short_name=board_name).first_or_404()
    page = request.args.get("page", 1, type=int)
    per_page = current_app.config["SETTINGS"].threads_per_page
    threads_paginated = (
        board.threads.filter(
            Thread.board_id.in_(get_visible_board_ids()), Thread.posts.any()
        )
        .order_by(Thread.is_pinned.desc(), Thread.bumped_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    form = PostForm()

    captcha_data = None
    captcha_token = None

    if current_app.config["SETTINGS"].captcha_enabled:
        captcha_data, _, captcha_token = generate_captcha()

    current_app.emit("board.opening", board=board)
    return render_template(
        "board.html",
        board=board,
        threads=threads_paginated.items,
        pagination=threads_paginated,
        form=form,
        captcha_data=captcha_data,
        captcha_token=captcha_token,
    )


@board_bp.route("/<string:board_name>/catalog", strict_slashes=False)
def board_catalog(board_name):
    board = Board.query.filter_by(short_name=board_name).first_or_404()
    per_page = current_app.config["SETTINGS"].threads_per_page
    from services.threads import get_board_threads

    threads = get_board_threads(board.id)
    from models import get_last_replies

    last_replies = get_last_replies([t.id for t in threads])
    return render_template(
        "catalog.html", board=board, threads=threads, last_replies=last_replies
    )


@board_bp.route("/<string:board_name>/thread/<int:thread_id>")
def thread(board_name, thread_id):
    board = Board.query.filter_by(short_name=board_name).first_or_404()
    from services.threads import get_thread

    thread = get_thread(thread_id)
    page = request.args.get("page", 1, type=int)
    per_page = current_app.config["SETTINGS"].posts_per_page
    posts_paginated = thread.posts.order_by(Post.created_at.asc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    form = PostForm()

    captcha_data = None
    captcha_token = None

    if current_app.config["SETTINGS"].captcha_enabled:
        captcha_data, _, captcha_token = generate_captcha()

    quote_text = ""
    reply_to = request.args.get("reply", type=int)
    if reply_to:
        quote_text = f">>{reply_to}\n"
    current_app.emit("thread.opening", thread=thread, board=board)
    return render_template(
        "thread.html",
        board=board,
        thread=thread,
        posts=posts_paginated.items,
        pagination=posts_paginated,
        form=form,
        quote_text=quote_text,
        captcha_data=captcha_data,
        captcha_token=captcha_token,
    )


@board_bp.route("/<string:board_name>/post", methods=["POST"])
@csrf_protect("post")
def create_post(board_name):
    board = Board.query.filter_by(short_name=board_name).first_or_404()
    form = PostForm()

    check_rate_limit()
    check_ban(request.remote_addr)

    if current_app.config["SETTINGS"].captcha_enabled:
        captcha_answer = request.form.get("captcha_answer", "")
        captcha_token = request.form.get("captcha_token", "")

        if not verify_captcha(captcha_answer, captcha_token):
            form.captcha_answer.errors = ["Invalid captcha code"]
            captcha_error = "Invalid captcha code"
            # Генерируем новую капчу
            captcha_data, _, captcha_token = generate_captcha()
            thread_id = request.args.get("thread_id", type=int)
            if thread_id:
                thread = Thread.query.get_or_404(thread_id)
                page = request.args.get("page", 1, type=int)
                per_page = current_app.config["SETTINGS"].posts_per_page
                posts_paginated = thread.posts.order_by(Post.created_at.asc()).paginate(
                    page=page, per_page=per_page, error_out=False
                )
                quote_text = ""
                reply_to = request.args.get("reply", type=int)
                if reply_to:
                    quote_text = f">>{reply_to}\n"
                return (
                    render_template(
                        "thread.html",
                        board=board,
                        thread=thread,
                        posts=posts_paginated.items,
                        pagination=posts_paginated,
                        form=form,
                        quote_text=quote_text,
                        captcha_data=captcha_data,
                        captcha_token=captcha_token,
                        captcha_error=captcha_error,
                    ),
                    400,
                )
            else:
                page = request.args.get("page", 1, type=int)
                per_page = current_app.config["SETTINGS"].threads_per_page
                threads_paginated = (
                    board.threads.filter(
                        Thread.board_id.in_(get_visible_board_ids()), Thread.posts.any()
                    )
                    .order_by(Thread.is_pinned.desc(), Thread.bumped_at.desc())
                    .paginate(page=page, per_page=per_page, error_out=False)
                )
                return (
                    render_template(
                        "board.html",
                        board=board,
                        threads=threads_paginated.items,
                        pagination=threads_paginated,
                        form=form,
                        captcha_data=captcha_data,
                        captcha_token=captcha_token,
                        captcha_error=captcha_error,
                    ),
                    400,
                )

    if form.validate_on_submit():
        thread_id = request.args.get("thread_id", type=int)
        sage = form.sage.data
        if thread_id:
            thread = Thread.query.get_or_404(thread_id)
            if thread.is_locked:
                abort(403, description=t("thread.closed"))
            if not form.files.data and not form.comment.data:
                form.comment.errors.append(t("comment_or_file_required"))
                return render_template("error.html", form=form), 400
        else:
            if not form.subject.data:
                form.subject.errors.append(t("subject_required"))
                return render_template("error.html", form=form), 400
            if not form.files.data and not form.comment.data:
                form.comment.errors.append(t("comment_or_file_required"))
                return render_template("error.html", form=form), 400
            thread = Thread(board_id=board.id)
            db.session.add(thread)
            db.session.flush()

        # Используем сервис для создания поста
        from services.posts import create_post

        post = create_post(board, thread, form, form.files.data, request.remote_addr)

        # Перенаправляем на страницу треда
        if thread_id:
            total_posts = thread.posts.count()
            per_page = current_app.config["SETTINGS"].posts_per_page
            last_page = (total_posts + per_page - 1) // per_page
            return redirect(
                url_for(
                    "board.thread",
                    board_name=board_name,
                    thread_id=thread_id,
                    page=last_page,
                )
            )
        else:
            return redirect(
                url_for("board.thread", board_name=board_name, thread_id=thread.id)
            )
    else:
        return render_template("error.html", form=form), 400


@board_bp.route("/<string:board_name>/delete/<int:post_id>", methods=["POST"])
@csrf_protect("delete_post")
def delete_post(board_name, post_id):
    post = Post.query.get_or_404(post_id)
    password = request.form.get("password")
    if not password or not check_password(password, post.password_hash):
        abort(403, description=t("wrong_password"))

    thread = post.thread
    board = thread.board
    is_op = thread.posts.order_by(Post.created_at.asc()).first().id == post.id

    if is_op:
        for p in thread.posts:
            for pf in p.files:
                try:
                    os.remove(
                        os.path.join(current_app.config["UPLOAD_FOLDER"], pf.file_path)
                    )
                    os.remove(
                        os.path.join(
                            current_app.config["UPLOAD_FOLDER"], "thumbs", pf.thumb_path
                        )
                    )
                except:
                    pass
            PostFTS.query.filter_by(post_id=p.id).delete()
        db.session.delete(thread)
        db.session.commit()
        current_app.emit(
            "content.changed", action="deleted", post=post, thread=thread, board=board
        )
        return redirect(url_for("board.board", board_name=board.short_name))
    else:
        for pf in post.files:
            try:
                os.remove(
                    os.path.join(current_app.config["UPLOAD_FOLDER"], pf.file_path)
                )
                os.remove(
                    os.path.join(
                        current_app.config["UPLOAD_FOLDER"], "thumbs", pf.thumb_path
                    )
                )
            except:
                pass
        PostFTS.query.filter_by(post_id=post.id).delete()
        db.session.delete(post)
        db.session.commit()
        current_app.emit(
            "content.changed", action="deleted", post=post, thread=thread, board=board
        )
        return redirect(
            url_for("board.thread", board_name=board.short_name, thread_id=thread.id)
        )


@board_bp.route("/<string:board_name>/search")
def board_search(board_name):
    board = Board.query.filter_by(short_name=board_name).first_or_404()
    query = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = 20
    results = []
    pagination = None
    if query:
        post_query = Post.query.join(Thread).filter(Thread.board_id == board.id)
        post_query = post_query.filter(
            Post.search_text.contains(query.lower()),
            Board.id.in_(get_visible_board_ids()),
            Board.id.in_(get_visible_board_ids()),
        ).order_by(Post.created_at.desc())
        pagination = post_query.paginate(page=page, per_page=per_page, error_out=False)
        results = pagination.items
    return render_template(
        "search.html", board=board, query=query, results=results, pagination=pagination
    )


@board_bp.route("/<string:board_name>/hide/<int:thread_id>")
def hide_thread(board_name, thread_id):
    resp = make_response(redirect(url_for("board.board", board_name=board_name)))
    hidden = request.cookies.get("hidden_threads", "").split(",")
    hidden = [h for h in hidden if h]
    if str(thread_id) not in hidden:
        hidden.append(str(thread_id))
    resp.set_cookie("hidden_threads", ",".join(hidden), max_age=30 * 24 * 3600)
    return resp


@board_bp.route("/<string:board_name>/report/<int:post_id>", methods=["GET", "POST"])
@csrf_protect("report")
def report_post(board_name, post_id):
    board = Board.query.filter_by(short_name=board_name).first_or_404()
    post = Post.query.get_or_404(post_id)

    # Генерируем капчу для формы (GET) и передаём в шаблон
    captcha_data = None
    captcha_token = None
    if current_app.config["SETTINGS"].captcha_enabled:
        from services.captcha import generate_captcha

        captcha_data, _, captcha_token = generate_captcha()

    if request.method == "POST":
        # Проверяем, включена ли система жалоб
        if not current_app.config["SETTINGS"].reports_enabled:
            flash(t("report_disabled"), "error")
            return redirect(
                url_for("board.thread", board_name=board_name, thread_id=post.thread_id)
            )

        # Stateless-проверка капчи
        if current_app.config["SETTINGS"].captcha_enabled:
            captcha_answer = request.form.get("captcha_answer", "").strip()
            captcha_token = request.form.get("captcha_token", "")
            from services.captcha import verify_captcha

            if not verify_captcha(captcha_answer, captcha_token):
                flash(t("captcha_error"), "error")
                return redirect(
                    url_for("board.report_post", board_name=board_name, post_id=post_id)
                )

        reason = request.form.get("reason", "")
        comment = request.form.get("comment", "")
        if not reason:
            flash(t("report_reason_required"), "error")
            return redirect(
                url_for("board.report_post", board_name=board_name, post_id=post_id)
            )

        report = Report(post_id=post.id, reason=reason, comment=comment)
        db.session.add(report)
        db.session.commit()
        flash(t("report_sent"), "success")
        return redirect(
            url_for("board.thread", board_name=board_name, thread_id=post.thread_id)
        )

    return render_template(
        "report.html",
        board=board,
        post=post,
        captcha_data=captcha_data,
        captcha_token=captcha_token,
    )


# ===== RSS =====
from flask import Response


def render_rss(template, **context):
    xml = render_template(template, **context)
    return Response(xml, mimetype="application/rss+xml")


@board_bp.route("/<string:board_name>/rss")
def board_rss(board_name):
    board = Board.query.filter_by(short_name=board_name).first_or_404()
    threads = (
        board.threads.filter(
            Thread.board_id.in_(get_visible_board_ids()), Thread.posts.any()
        )
        .order_by(Thread.created_at.desc())
        .limit(20)
        .all()
    )
    site_url = current_app.config["SETTINGS"].site_url
    return render_rss("rss_board.xml", board=board, threads=threads, site_url=site_url)


@board_bp.route("/<string:board_name>/thread/<int:thread_id>/rss")
def thread_rss(board_name, thread_id):
    board = Board.query.filter_by(short_name=board_name).first_or_404()
    from services.threads import get_thread

    thread = get_thread(thread_id)
    posts = thread.posts.order_by(Post.created_at.desc()).limit(50).all()
    site_url = current_app.config["SETTINGS"].site_url
    return render_rss(
        "rss_thread.xml", board=board, thread=thread, posts=posts, site_url=site_url
    )
