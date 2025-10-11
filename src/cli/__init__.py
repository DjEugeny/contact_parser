#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLI entry points for the project."""

__all__ = ["InteractiveMenu"]


def __getattr__(name):
    if name == "InteractiveMenu":
        from .interactive_menu import InteractiveMenu

        return InteractiveMenu
    raise AttributeError(name)
