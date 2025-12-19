
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from PySide6.QtWidgets import QApplication
from src.gui.main_window import MainWindow

def verify():
    print("Verifying GUI instantiation...")
    try:
        app = QApplication(sys.argv)
        print("QApplication created.")
        
        window = MainWindow()
        print("MainWindow instantiated successfully.")
        
        # Check if key components exist
        if not hasattr(window, 'navigation_interface'):
            print("ERROR: navigation_interface missing")
            return False
            
        if not hasattr(window, 'tool_stack'):
            print("ERROR: tool_stack missing")
            return False
            
        print("MainWindow components verified.")
        return True
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = verify()
    if success:
        print("VERIFICATION PASSED")
        sys.exit(0)
    else:
        print("VERIFICATION FAILED")
        sys.exit(1)
