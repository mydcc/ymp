import sys
from ymp.mpris import _try_import_mpris, MPRIS_AVAILABLE

def test_mpris_safety():
    # Attempt to trigger the import logic
    _try_import_mpris()

    # Check if it survived without crashing
    print(f"MPRIS Available: {MPRIS_AVAILABLE}")
    print("Safety check passed (no crash).")

if __name__ == "__main__":
    test_mpris_safety()
