# -*- coding: utf-8 -*-
"""
SafeMed 脱敏工具主入口
新的现代化UI已在 ui_app.py 中实现
"""
from .ui_app import ModernSafeMedApp as App, main

__all__ = ['App', 'main']


if __name__ == "__main__":
    main()
