"""Local operator CLI: database init, user provisioning, dev server.

    python -m backend.cli init-db
    python -m backend.cli create-user --username alice
    python -m backend.cli list-users
    python -m backend.cli serve --host 127.0.0.1 --port 8000

There is no registration endpoint and no default account; passwords are only
accepted interactively via getpass or a single line on stdin.
"""

from __future__ import annotations

import argparse
import getpass
import sys

from sqlalchemy import select

from .config import Settings
from .db import Database
from .models import User
from .security import hash_password

MIN_PASSWORD_LENGTH = 8


def _read_password(from_stdin: bool) -> str:
    if from_stdin:
        password = sys.stdin.readline().rstrip("\n")
    else:
        password = getpass.getpass("密码: ")
        confirm = getpass.getpass("再次输入密码: ")
        if password != confirm:
            raise SystemExit("两次输入的密码不一致")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise SystemExit(f"密码至少 {MIN_PASSWORD_LENGTH} 位")
    return password


def _cmd_init_db(_args: argparse.Namespace) -> int:
    settings = Settings.from_env()
    db = Database(settings.database_url)
    db.create_all()
    db.dispose()
    print(f"数据库已就绪: {settings.database_url}")
    return 0


def _cmd_create_user(args: argparse.Namespace) -> int:
    username = args.username.strip()
    if not username:
        raise SystemExit("用户名不能为空")
    password = _read_password(args.password_stdin)

    settings = Settings.from_env()
    db = Database(settings.database_url)
    db.create_all()
    try:
        with db.session() as session:
            if session.scalar(select(User).where(User.username == username)):
                raise SystemExit(f"用户已存在: {username}")
            session.add(User(username=username, password_hash=hash_password(password)))
    finally:
        db.dispose()
    print(f"已创建用户: {username}")
    return 0


def _cmd_list_users(_args: argparse.Namespace) -> int:
    settings = Settings.from_env()
    db = Database(settings.database_url)
    db.create_all()
    try:
        with db.session() as session:
            users = session.scalars(select(User).order_by(User.created_at)).all()
            for user in users:
                print(f"{user.username}\t{user.id}")
            if not users:
                print("(无用户)")
    finally:
        db.dispose()
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    from .app import create_app

    uvicorn.run(create_app(Settings.from_env()), host=args.host, port=args.port, log_level="info")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m backend.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-db", help="创建 SQLite 表结构").set_defaults(func=_cmd_init_db)

    create = sub.add_parser("create-user", help="创建账号（无注册接口）")
    create.add_argument("--username", required=True)
    create.add_argument(
        "--password-stdin",
        action="store_true",
        help="从 stdin 读取一行密码（自动化用，避免终端回显）",
    )
    create.set_defaults(func=_cmd_create_user)

    sub.add_parser("list-users", help="列出账号").set_defaults(func=_cmd_list_users)

    serve = sub.add_parser("serve", help="启动后端（同时托管 frontend）")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.set_defaults(func=_cmd_serve)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
