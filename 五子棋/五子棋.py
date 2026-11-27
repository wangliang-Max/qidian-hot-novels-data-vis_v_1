# -*- coding: utf-8 -*-
"""控制台五子棋（10×10，双人）。

操作：
    行,列     落子，例如 3,4（行列均为 0-9，也接受中文逗号）
    S         保存棋局
    L         读取棋局
    Q         退出
"""

import os
import pickle

SIZE = 10
EMPTY, BLACK, WHITE = 0, 1, 2
DIRECTIONS = ((1, 0), (0, 1), (1, 1), (1, -1))
SAVE_DEFAULT = "五子棋存档.pkl"


def new_board():
    return [[EMPTY] * SIZE for _ in range(SIZE)]


def in_range(x, y):
    return 0 <= x < SIZE and 0 <= y < SIZE


def count_line(board, x, y, dx, dy, color):
    """从 (x,y) 出发，沿 (dx,dy) 正反两个方向数同色连子（含自身）。"""
    total = 1
    for sign in (1, -1):
        nx, ny = x + dx * sign, y + dy * sign
        while in_range(nx, ny) and board[nx][ny] == color:
            total += 1
            nx += dx * sign
            ny += dy * sign
    return total


def is_win(board, x, y):
    """任意方向连成 5 子即胜。"""
    color = board[x][y]
    return any(count_line(board, x, y, dx, dy, color) >= 5
               for dx, dy in DIRECTIONS)


def print_board(board):
    print("\n        五子棋（10×10）")
    print("     " + " ".join("%2d" % c for c in range(SIZE)))
    for i in range(SIZE):
        cells = []
        for j in range(SIZE):
            cells.append({EMPTY: "空", BLACK: "黑", WHITE: "白"}[board[i][j]])
        print("%2d   %s" % (i, " ".join(cells)))
    print()


def save_game(board, who, path):
    with open(path, "wb") as fh:
        pickle.dump({"board": board, "who": who}, fh)
    print("已保存到：%s" % os.path.abspath(path))


def load_game(path):
    with open(path, "rb") as fh:
        data = pickle.load(fh)
    board = data.get("board")
    who = data.get("who")
    if (not isinstance(board, list) or len(board) != SIZE
            or any(not isinstance(row, list) or len(row) != SIZE for row in board)):
        raise ValueError("存档里的棋盘格式不对")
    return board, bool(who)


def parse_move(text):
    """把 '3,4' / '3，4' 解析成 (3, 4)，非法返回 None。"""
    parts = [p.strip() for p in text.replace("，", ",").split(",")]
    if len(parts) != 2:
        return None
    try:
        x, y = int(parts[0]), int(parts[1])
    except ValueError:
        return None
    return x, y


def play():
    board = new_board()
    who = True          # True = 黑方，False = 白方
    print_board(board)

    while True:
        side = "黑方" if who else "白方"
        try:
            text = input("请下子（行,列），%s；S 保存 / L 读取 / Q 退出： " % side).strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见。")
            return

        if not text:
            continue
        cmd = text.upper()
        if cmd == "Q":
            print("再见。")
            return
        if cmd == "S":
            path = input("保存路径（直接回车用 %s）： " % SAVE_DEFAULT).strip() or SAVE_DEFAULT
            try:
                save_game(board, who, path)
            except OSError as exc:
                print("保存失败：%s" % exc)
            continue
        if cmd == "L":
            path = input("棋盘路径（直接回车用 %s）： " % SAVE_DEFAULT).strip() or SAVE_DEFAULT
            try:
                board, who = load_game(path)
                print("已读取：%s" % os.path.abspath(path))
                print_board(board)
            except (OSError, ValueError, pickle.UnpicklingError) as exc:
                print("读取失败：%s" % exc)
            continue

        move = parse_move(text)
        if move is None:
            print("格式不对，请输入“行,列”，例如 3,4。")
            continue
        x, y = move
        if not in_range(x, y):
            print("坐标超出范围，行列都应在 0-%d 之间。" % (SIZE - 1))
            continue
        if board[x][y] != EMPTY:
            print("该位置已经有子，请重下。")
            continue

        board[x][y] = BLACK if who else WHITE
        print_board(board)
        if is_win(board, x, y):
            print("%s赢！" % side)
            return
        who = not who


if __name__ == "__main__":
    play()
