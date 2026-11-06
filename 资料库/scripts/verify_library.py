"""Portable archive verification."""
from library import verify

if __name__ == "__main__":
    raise SystemExit(0 if verify() else 1)
