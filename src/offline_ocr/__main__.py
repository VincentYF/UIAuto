import sys
from offline_ocr.cli.main import main

if __name__ == "__main__":
    # If standard run, default to CLI or GUI based on parameters
    if len(sys.argv) == 1:
        # No arguments given, launch GUI
        from offline_ocr.gui.main_window import run_gui
        run_gui()
    else:
        main()
