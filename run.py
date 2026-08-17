#!/usr/bin/env python3
"""Entry point: python run.py [--config my.json]"""
import argparse
from neonhead.app import App

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="neon head")
    ap.add_argument("--config", default=None, help="path to a config json (merged over defaults)")
    App(ap.parse_args().config).run()
