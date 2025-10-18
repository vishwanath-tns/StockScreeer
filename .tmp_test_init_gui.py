import tkinter as tk
from scanner_gui import ScannerGUI
root = tk.Tk()
root.withdraw()
ScannerGUI(root)
print('ScannerGUI initialized OK')
root.destroy()