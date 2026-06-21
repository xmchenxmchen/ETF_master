"""讓 tests 能以 `from core...` 匯入：把 v2 專案根目錄加入 sys.path。"""
import os
import sys

V2_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if V2_ROOT not in sys.path:
    sys.path.insert(0, V2_ROOT)
