#!/usr/bin/env python3
"""
Final test of dashboard status checking functionality.
"""

print('🔍 Testing Dashboard Status Methods...')

import reporting_adv_decl as rad
from gui.tabs.dashboard import DashboardTab
import tkinter as tk

# Create dashboard instance
root = tk.Tk()
root.withdraw()
dashboard = DashboardTab(tk.Frame(root))

# Get engine and test each status method
engine = rad.engine()

print('\n📊 Testing database table status:')

# Test BHAV status
bhav_result = dashboard.check_bhav_data(engine)
print(f'BHAV Data: {bhav_result["status"]} ({bhav_result["color"]})')
if 'details' in bhav_result:
    print(f'  Details: {bhav_result["details"]}')

# Test SMA status  
sma_result = dashboard.check_sma_data(engine)
print(f'SMA Data: {sma_result["status"]} ({sma_result["color"]})')
if 'details' in sma_result:
    print(f'  Details: {sma_result["details"]}')

# Test RSI status
rsi_result = dashboard.check_rsi_data(engine)  
print(f'RSI Data: {rsi_result["status"]} ({rsi_result["color"]})')
if 'details' in rsi_result:
    print(f'  Details: {rsi_result["details"]}')

# Test Trend status
trend_result = dashboard.check_trend_data(engine)
print(f'Trend Data: {trend_result["status"]} ({trend_result["color"]})')
if 'details' in trend_result:
    print(f'  Details: {trend_result["details"]}')

root.destroy()
print('\n✅ Dashboard status test completed successfully!')

# Summary
if all(result["status"] != "❌ No Table" for result in [bhav_result, sma_result, rsi_result, trend_result]):
    print('\n🎉 All tables detected correctly! Dashboard fix is working.')
else:
    print('\n⚠️  Some tables still showing as missing.')