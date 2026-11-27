# -*- coding: utf-8 -*-
"""让 tests/ 里能直接 ``import fund``，不依赖 pip install -e ."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
