"""
FNO Import Wizard
A step-by-step wizard for importing NSE F&O bhavcopy data

Features:
- Step 1: Select folder containing FNO files
- Step 2: Preview files and check import status
- Step 3: Select analysis options (compare with previous day)
- Step 4: Import and analyze
"""

import os
import sys
from datetime import datetime, date
from typing import Optional, Dict

from PyQt5.QtWidgets import (
    QApplication, QWizard, QWizardPage, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFileDialog, QLineEdit, QGroupBox, QCheckBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar, QTextEdit,
    QRadioButton, QButtonGroup, QComboBox, QMessageBox, QFrame, QSplitter
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QColor

# Add parent path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fno.database.schema import create_database, get_table_stats, FNO_DATABASE
from fno.services.fno_parser import (
    find_fno_files, parse_futures_file, parse_options_file, 
    md5_of_file, parse_date_from_filename
)
from fno.services.fno_db_service import FNODBService


class ImportWorker(QThread):
    """Worker thread for importing FNO data."""
    progress = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, folder_path: str, run_analysis: bool = True, 
                 analyze_nifty: bool = True, analyze_banknifty: bool = True):
        super().__init__()
        self.folder_path = folder_path
        self.run_analysis = run_analysis
        self.analyze_nifty = analyze_nifty
        self.analyze_banknifty = analyze_banknifty
        self.db_service = None
    
    def run(self):
        try:
            self.db_service = FNODBService()
            results = {
                'futures_imported': 0,
                'futures_updated': 0,
                'options_imported': 0,
                'options_updated': 0,
                'trade_date': None,
                'analysis_done': False,
                'errors': []
            }
            
            # Find files
            files = find_fno_files(self.folder_path)
            
            if not files['futures'] and not files['options']:
                self.error.emit("No FNO files found in the selected folder")
                return
            
            # Import futures
            if files['futures']:
                self.progress.emit(f"📊 Parsing futures file: {os.path.basename(files['futures'])}")
                try:
                    df, trade_date = parse_futures_file(files['futures'])
                    results['trade_date'] = trade_date
                    
                    self.progress.emit(f"   Found {len(df)} futures contracts for {trade_date}")
                    
                    # Check if already imported
                    if self.db_service.is_already_imported(trade_date, 'futures'):
                        self.progress.emit(f"⚠️  Futures for {trade_date} already imported - updating...")
                    
                    self.progress.emit("   Importing to database...")
                    imported, updated = self.db_service.insert_futures_data(df, trade_date)
                    results['futures_imported'] = imported
                    results['futures_updated'] = updated
                    
                    # Log import
                    checksum = md5_of_file(files['futures'])
                    self.db_service.log_import(
                        trade_date, 'futures', os.path.basename(files['futures']),
                        checksum, imported, updated
                    )
                    
                    self.progress.emit(f"✅ Futures: {imported} records imported, {updated} updated")
                    
                except Exception as e:
                    error_msg = f"Error importing futures: {str(e)}"
                    results['errors'].append(error_msg)
                    self.progress.emit(f"❌ {error_msg}")
            
            # Import options
            if files['options']:
                self.progress.emit(f"\n📊 Parsing options file: {os.path.basename(files['options'])}")
                try:
                    df, trade_date = parse_options_file(files['options'])
                    if results['trade_date'] is None:
                        results['trade_date'] = trade_date
                    
                    self.progress.emit(f"   Found {len(df)} options contracts for {trade_date}")
                    
                    # Check if already imported
                    if self.db_service.is_already_imported(trade_date, 'options'):
                        self.progress.emit(f"⚠️  Options for {trade_date} already imported - updating...")
                    
                    self.progress.emit("   Importing to database (this may take a moment)...")
                    imported, updated = self.db_service.insert_options_data(df, trade_date)
                    results['options_imported'] = imported
                    results['options_updated'] = updated
                    
                    # Log import
                    checksum = md5_of_file(files['options'])
                    self.db_service.log_import(
                        trade_date, 'options', os.path.basename(files['options']),
                        checksum, imported, updated
                    )
                    
                    self.progress.emit(f"✅ Options: {imported} records imported, {updated} updated")
                    
                except Exception as e:
                    error_msg = f"Error importing options: {str(e)}"
                    results['errors'].append(error_msg)
                    self.progress.emit(f"❌ {error_msg}")
            
            # Update symbol master
            if results['trade_date']:
                self.progress.emit("\n📝 Updating symbol master...")
                self.db_service.update_symbol_master(results['trade_date'])
            
            # Run analysis
            if self.run_analysis and results['trade_date']:
                self.progress.emit("\n🔍 Running analysis...")
                
                # Futures analysis
                self.progress.emit("   Analyzing futures buildup...")
                count = self.db_service.save_futures_analysis(results['trade_date'])
                self.progress.emit(f"   ✅ Analyzed {count} futures contracts")
                
                # Option chain analysis
                symbols_to_analyze = []
                if self.analyze_nifty:
                    symbols_to_analyze.append('NIFTY')
                if self.analyze_banknifty:
                    symbols_to_analyze.append('BANKNIFTY')
                
                for symbol in symbols_to_analyze:
                    self.progress.emit(f"   Analyzing {symbol} option chain...")
                    success = self.db_service.save_option_chain_summary(results['trade_date'], symbol)
                    if success:
                        self.progress.emit(f"   ✅ {symbol} analysis complete")
                    else:
                        self.progress.emit(f"   ⚠️  No {symbol} data found")
                
                results['analysis_done'] = True
            
            self.progress.emit("\n" + "=" * 50)
            self.progress.emit("🎉 Import completed successfully!")
            self.finished.emit(results)
            
        except Exception as e:
            self.error.emit(str(e))


class FolderSelectionPage(QWizardPage):
    """Page 1: Select folder containing FNO files."""
    
    def __init__(self):
        super().__init__()
        self.setTitle("Select FNO Data Folder")
        self.setSubTitle("Choose the folder containing NSE F&O bhavcopy files (fo*.csv, op*.csv)")
        
        layout = QVBoxLayout(self)
        
        # Folder selection
        folder_group = QGroupBox("📁 Data Folder")
        folder_layout = QHBoxLayout(folder_group)
        
        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("Select folder with FNO files...")
        self.folder_edit.textChanged.connect(self.completeChanged)
        folder_layout.addWidget(self.folder_edit)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_folder)
        folder_layout.addWidget(browse_btn)
        
        layout.addWidget(folder_group)
        
        # Recent folders (placeholder for future)
        recent_group = QGroupBox("📋 Recent Folders")
        recent_layout = QVBoxLayout(recent_group)
        recent_layout.addWidget(QLabel("(Recent folders will appear here)"))
        layout.addWidget(recent_group)
        
        # Info
        info_label = QLabel(
            "ℹ️ Expected files:\n"
            "• fo[DDMMYY].csv - Futures bhavcopy\n"
            "• op[DDMMYY].csv - Options bhavcopy"
        )
        info_label.setStyleSheet("color: #666;")
        layout.addWidget(info_label)
        
        layout.addStretch()
        
        # Register field
        self.registerField("folder_path*", self.folder_edit)
    
    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select FNO Data Folder",
            "D:\\nsedata\\fno bhav copies"
        )
        if folder:
            self.folder_edit.setText(folder)
    
    def isComplete(self):
        folder = self.folder_edit.text()
        return bool(folder) and os.path.isdir(folder)


class FilePreviewPage(QWizardPage):
    """Page 2: Preview files and check import status."""
    
    def __init__(self):
        super().__init__()
        self.setTitle("Preview & Import Status")
        self.setSubTitle("Review the files found and their import status")
        
        layout = QVBoxLayout(self)
        
        # Files found
        files_group = QGroupBox("📄 Files Found")
        files_layout = QVBoxLayout(files_group)
        
        self.files_table = QTableWidget()
        self.files_table.setColumnCount(5)
        self.files_table.setHorizontalHeaderLabels([
            'Type', 'Filename', 'Trade Date', 'Size', 'Status'
        ])
        self.files_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.files_table.setMinimumHeight(120)
        files_layout.addWidget(self.files_table)
        
        layout.addWidget(files_group)
        
        # Database status
        db_group = QGroupBox("🗄️ Database Status")
        db_layout = QGridLayout(db_group)
        
        self.db_status_label = QLabel("Checking database...")
        db_layout.addWidget(self.db_status_label, 0, 0, 1, 2)
        
        self.futures_count_label = QLabel("Futures records: -")
        db_layout.addWidget(self.futures_count_label, 1, 0)
        
        self.options_count_label = QLabel("Options records: -")
        db_layout.addWidget(self.options_count_label, 1, 1)
        
        self.last_import_label = QLabel("Last import: -")
        db_layout.addWidget(self.last_import_label, 2, 0, 1, 2)
        
        layout.addWidget(db_group)
        
        # Warning if already imported
        self.warning_frame = QFrame()
        self.warning_frame.setStyleSheet("""
            QFrame {
                background-color: #fff3cd;
                border: 1px solid #ffc107;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        warning_layout = QVBoxLayout(self.warning_frame)
        self.warning_label = QLabel()
        self.warning_label.setWordWrap(True)
        warning_layout.addWidget(self.warning_label)
        self.warning_frame.hide()
        
        layout.addWidget(self.warning_frame)
        layout.addStretch()
    
    def initializePage(self):
        """Called when page is shown."""
        folder = self.field("folder_path")
        self.check_files(folder)
        self.check_database()
    
    def check_files(self, folder: str):
        """Check files in the selected folder."""
        files = find_fno_files(folder)
        
        self.files_table.setRowCount(0)
        
        for file_type, filepath in files.items():
            if filepath:
                row = self.files_table.rowCount()
                self.files_table.insertRow(row)
                
                # Type
                self.files_table.setItem(row, 0, QTableWidgetItem(file_type.capitalize()))
                
                # Filename
                self.files_table.setItem(row, 1, QTableWidgetItem(os.path.basename(filepath)))
                
                # Trade date
                trade_date = parse_date_from_filename(filepath)
                date_str = trade_date.strftime('%Y-%m-%d') if trade_date else 'Unknown'
                self.files_table.setItem(row, 2, QTableWidgetItem(date_str))
                
                # Size
                size = os.path.getsize(filepath)
                size_str = f"{size/1024:.1f} KB" if size < 1024*1024 else f"{size/1024/1024:.1f} MB"
                self.files_table.setItem(row, 3, QTableWidgetItem(size_str))
                
                # Status - check if already imported
                try:
                    db = FNODBService()
                    if trade_date and db.is_already_imported(trade_date, file_type):
                        status_item = QTableWidgetItem("✅ Already Imported")
                        status_item.setForeground(QColor('#28a745'))
                        
                        # Show warning
                        self.warning_label.setText(
                            f"⚠️ Data for {date_str} has already been imported. "
                            "Continuing will update the existing records."
                        )
                        self.warning_frame.show()
                    else:
                        status_item = QTableWidgetItem("🆕 New")
                        status_item.setForeground(QColor('#007bff'))
                except:
                    status_item = QTableWidgetItem("❓ Unknown")
                
                self.files_table.setItem(row, 4, status_item)
    
    def check_database(self):
        """Check database status."""
        try:
            stats = get_table_stats()
            self.db_status_label.setText("✅ Database connected")
            self.futures_count_label.setText(f"Futures records: {stats.get('nse_futures', 0):,}")
            self.options_count_label.setText(f"Options records: {stats.get('nse_options', 0):,}")
            
            db = FNODBService()
            last_date = db.get_latest_trade_date()
            if last_date:
                self.last_import_label.setText(f"Last import: {last_date}")
            else:
                self.last_import_label.setText("Last import: No data yet")
                
        except Exception as e:
            self.db_status_label.setText(f"❌ Database error: {str(e)}")


class AnalysisOptionsPage(QWizardPage):
    """Page 3: Select analysis options."""
    
    def __init__(self):
        super().__init__()
        self.setTitle("Analysis Options")
        self.setSubTitle("Configure what analysis to run after importing")
        
        layout = QVBoxLayout(self)
        
        # Import options
        import_group = QGroupBox("📥 Import Options")
        import_layout = QVBoxLayout(import_group)
        
        self.chk_compare_prev = QCheckBox("Compare with previous day's data (OI changes)")
        self.chk_compare_prev.setChecked(True)
        import_layout.addWidget(self.chk_compare_prev)
        
        layout.addWidget(import_group)
        
        # Analysis options
        analysis_group = QGroupBox("🔍 Analysis Options")
        analysis_layout = QVBoxLayout(analysis_group)
        
        self.chk_run_analysis = QCheckBox("Run analysis after import")
        self.chk_run_analysis.setChecked(True)
        self.chk_run_analysis.toggled.connect(self.toggle_analysis_options)
        analysis_layout.addWidget(self.chk_run_analysis)
        
        # Sub-options
        sub_layout = QVBoxLayout()
        sub_layout.setContentsMargins(20, 5, 0, 5)
        
        self.chk_futures_buildup = QCheckBox("Futures buildup analysis (Long/Short detection)")
        self.chk_futures_buildup.setChecked(True)
        sub_layout.addWidget(self.chk_futures_buildup)
        
        self.chk_nifty_chain = QCheckBox("NIFTY option chain analysis (Support/Resistance)")
        self.chk_nifty_chain.setChecked(True)
        sub_layout.addWidget(self.chk_nifty_chain)
        
        self.chk_banknifty_chain = QCheckBox("BANKNIFTY option chain analysis")
        self.chk_banknifty_chain.setChecked(True)
        sub_layout.addWidget(self.chk_banknifty_chain)
        
        analysis_layout.addLayout(sub_layout)
        layout.addWidget(analysis_group)
        
        # Info about analysis
        info_group = QGroupBox("ℹ️ Analysis Details")
        info_layout = QVBoxLayout(info_group)
        info_label = QLabel(
            "<b>Futures Buildup Analysis:</b><br>"
            "• LONG_BUILDUP: Price ↑ + OI ↑<br>"
            "• SHORT_BUILDUP: Price ↓ + OI ↑<br>"
            "• LONG_UNWINDING: Price ↓ + OI ↓<br>"
            "• SHORT_COVERING: Price ↑ + OI ↓<br><br>"
            "<b>Option Chain Analysis:</b><br>"
            "• Support levels (highest PE OI)<br>"
            "• Resistance levels (highest CE OI)<br>"
            "• PCR (Put Call Ratio)<br>"
            "• Max Pain strike"
        )
        info_layout.addWidget(info_label)
        layout.addWidget(info_group)
        
        layout.addStretch()
        
        # Register fields
        self.registerField("run_analysis", self.chk_run_analysis)
        self.registerField("analyze_nifty", self.chk_nifty_chain)
        self.registerField("analyze_banknifty", self.chk_banknifty_chain)
    
    def toggle_analysis_options(self, checked: bool):
        """Enable/disable analysis sub-options."""
        self.chk_futures_buildup.setEnabled(checked)
        self.chk_nifty_chain.setEnabled(checked)
        self.chk_banknifty_chain.setEnabled(checked)


class ImportProgressPage(QWizardPage):
    """Page 4: Import progress and results."""
    
    def __init__(self):
        super().__init__()
        self.setTitle("Importing Data")
        self.setSubTitle("Please wait while data is being imported and analyzed")
        
        self.import_complete = False
        self.worker = None
        
        layout = QVBoxLayout(self)
        
        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        layout.addWidget(self.progress_bar)
        
        # Log
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: Consolas, monospace;
                font-size: 11px;
            }
        """)
        layout.addWidget(self.log_text)
        
        # Results summary
        self.results_group = QGroupBox("📊 Results Summary")
        self.results_group.hide()
        results_layout = QGridLayout(self.results_group)
        
        self.lbl_futures = QLabel("Futures: -")
        results_layout.addWidget(self.lbl_futures, 0, 0)
        
        self.lbl_options = QLabel("Options: -")
        results_layout.addWidget(self.lbl_options, 0, 1)
        
        self.lbl_analysis = QLabel("Analysis: -")
        results_layout.addWidget(self.lbl_analysis, 1, 0, 1, 2)
        
        layout.addWidget(self.results_group)
    
    def initializePage(self):
        """Start import when page is shown."""
        self.log_text.clear()
        self.import_complete = False
        self.results_group.hide()
        
        folder = self.field("folder_path")
        run_analysis = self.field("run_analysis")
        analyze_nifty = self.field("analyze_nifty")
        analyze_banknifty = self.field("analyze_banknifty")
        
        self.log("=" * 50)
        self.log("Starting FNO Data Import")
        self.log(f"Folder: {folder}")
        self.log("=" * 50 + "\n")
        
        # Start worker
        self.worker = ImportWorker(folder, run_analysis, analyze_nifty, analyze_banknifty)
        self.worker.progress.connect(self.log)
        self.worker.finished.connect(self.on_import_finished)
        self.worker.error.connect(self.on_import_error)
        self.worker.start()
    
    def log(self, message: str):
        """Add message to log."""
        self.log_text.append(message)
    
    def on_import_finished(self, results: dict):
        """Handle import completion."""
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        
        self.lbl_futures.setText(
            f"Futures: {results['futures_imported']} imported, {results['futures_updated']} updated"
        )
        self.lbl_options.setText(
            f"Options: {results['options_imported']} imported, {results['options_updated']} updated"
        )
        self.lbl_analysis.setText(
            f"Analysis: {'✅ Completed' if results['analysis_done'] else '⏭️ Skipped'}"
        )
        
        self.results_group.show()
        self.import_complete = True
        self.completeChanged.emit()
    
    def on_import_error(self, error: str):
        """Handle import error."""
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.log(f"\n❌ ERROR: {error}")
        
        QMessageBox.critical(self, "Import Error", f"An error occurred:\n{error}")
    
    def isComplete(self):
        return self.import_complete


class FNOImportWizard(QWizard):
    """Main wizard for importing FNO data."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("NSE F&O Data Import Wizard")
        self.setWizardStyle(QWizard.ModernStyle)
        self.setMinimumSize(700, 550)
        
        # Set window icon if available
        try:
            self.setWindowIcon(QIcon('assets/icon.png'))
        except:
            pass
        
        # Add pages
        self.addPage(FolderSelectionPage())
        self.addPage(FilePreviewPage())
        self.addPage(AnalysisOptionsPage())
        self.addPage(ImportProgressPage())
        
        # Button labels
        self.setButtonText(QWizard.NextButton, "Next →")
        self.setButtonText(QWizard.BackButton, "← Back")
        self.setButtonText(QWizard.FinishButton, "Close")
        self.setButtonText(QWizard.CancelButton, "Cancel")
        
        # Ensure database exists
        self.ensure_database()
    
    def ensure_database(self):
        """Ensure FNO database and tables exist."""
        try:
            create_database()
        except Exception as e:
            QMessageBox.warning(
                self, "Database Warning",
                f"Could not verify database:\n{str(e)}\n\nThe wizard may not work properly."
            )


def main():
    """Run the import wizard."""
    app = QApplication(sys.argv)
    
    # Apply Fusion style (works well with custom colors)
    app.setStyle('Fusion')
    
    wizard = FNOImportWizard()
    
    # Apply stylesheet for better readability
    wizard.setStyleSheet("""
        QWizard {
            background-color: #2d2d2d;
        }
        QWizardPage {
            background-color: #2d2d2d;
        }
        QLabel {
            color: #ffffff;
        }
        QGroupBox {
            color: #00aaff;
            font-weight: bold;
            border: 1px solid #555;
            border-radius: 5px;
            margin-top: 12px;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
            color: #00aaff;
        }
        QLineEdit {
            background-color: #3d3d3d;
            color: #ffffff;
            border: 1px solid #555;
            padding: 5px;
            border-radius: 3px;
        }
        QPushButton {
            background-color: #0d6efd;
            color: white;
            border: none;
            padding: 6px 15px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #0b5ed7;
        }
        QCheckBox {
            color: #ffffff;
            spacing: 8px;
        }
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
        }
        QRadioButton {
            color: #ffffff;
        }
        QTableWidget {
            background-color: #1e1e1e;
            color: #ffffff;
            gridline-color: #444;
            border: 1px solid #444;
        }
        QTableWidget::item {
            color: #ffffff;
            padding: 5px;
        }
        QHeaderView::section {
            background-color: #3d3d3d;
            color: #ffffff;
            padding: 5px;
            border: 1px solid #555;
            font-weight: bold;
        }
        QTextEdit {
            background-color: #1e1e1e;
            color: #d4d4d4;
            border: 1px solid #444;
        }
        QProgressBar {
            background-color: #3d3d3d;
            border: 1px solid #555;
            border-radius: 3px;
            text-align: center;
            color: white;
        }
        QProgressBar::chunk {
            background-color: #0d6efd;
        }
        QComboBox {
            background-color: #3d3d3d;
            color: #ffffff;
            border: 1px solid #555;
            padding: 5px;
            border-radius: 3px;
        }
        QComboBox::drop-down {
            border: none;
        }
        QComboBox QAbstractItemView {
            background-color: #3d3d3d;
            color: #ffffff;
            selection-background-color: #0d6efd;
        }
    """)
    
    wizard.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
