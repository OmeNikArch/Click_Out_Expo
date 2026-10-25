#!/usr/bin/env python3
"""ПИР Экспо: генератор настоящей карты на планах организатора.

`python3 events/pir_plan.py && python3 events/pir_map.py`
"""
import pathlib, runpy
runpy.run_path(str(pathlib.Path(__file__).with_name('pir_map_real.py')), run_name='__main__')
