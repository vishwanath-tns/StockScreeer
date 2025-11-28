import sys
import os
sys.path.append('d:/MyProjects/StockScreeer')
os.chdir('d:/MyProjects/StockScreeer')

from services.market_breadth_service import get_stocks_in_category

print('Testing Load Stocks service function...')

# Test with a common category
test_category = 'Very Bullish (8 to 10)'
print(f'Testing category: {test_category}')

result = get_stocks_in_category(test_category, trade_date=None)

if result.get('success'):
    stocks = result.get('stocks', [])
    print(f'Successfully loaded {len(stocks)} stocks')
    if stocks:
        sample_symbols = [s.get('symbol', 'N/A') for s in stocks[:5]]
        print(f'Sample stocks: {sample_symbols}')
    else:
        print('No stocks found in this category')
else:
    error = result.get('error', 'Unknown error')
    print(f'Failed to load stocks: {error}')

print('Service test completed!')