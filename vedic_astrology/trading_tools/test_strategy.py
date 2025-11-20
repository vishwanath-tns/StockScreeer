from trading_strategy import TradingStrategyGenerator

print('🧪 Testing Trading Strategy Generator...')
generator = TradingStrategyGenerator()
strategy = generator.generate_daily_strategy()
print('✅ Daily strategy generated successfully')
print(f'Strategy keys: {list(strategy.keys())}')

if 'moon_position' in strategy:
    moon = strategy['moon_position']
    print(f'Moon: {moon["sign"]} {moon["degree"]:.1f}° ({moon["element"]})')

if 'market_outlook' in strategy:
    outlook = strategy['market_outlook']
    print(f'Market outlook: {outlook.get("overall_outlook", "N/A")}')

print('✅ Trading strategy test complete')