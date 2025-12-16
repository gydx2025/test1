# -*- coding: utf-8 -*-
"""
PyQt UI 模块
"""

try:
    from .real_estate_query_app import RealEstateQueryApp
    __all__ = ['RealEstateQueryApp']
except ImportError as e:
    print(f"Warning: Cannot import PyQt5 UI components: {e}")
    print("Please install PyQt5: pip install PyQt5")
    __all__ = []