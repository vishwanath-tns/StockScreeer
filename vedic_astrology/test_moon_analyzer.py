from moon_zodiac_analyzer import MoonZodiacAnalyzer

print('🧪 Testing Moon Zodiac Analyzer...')
try:
    analyzer = MoonZodiacAnalyzer()
    current_influence = analyzer.get_current_market_influence()
    print('✅ Current market influence calculated')
    print(f'Influence keys: {list(current_influence.keys())}')
    
    if 'moon_zodiac' in current_influence:
        print(f'Current moon: {current_influence["moon_zodiac"]}')
    if 'volatility_factor' in current_influence:
        print(f'Volatility factor: {current_influence["volatility_factor"]}')
    
    # Test weekly analysis
    weekly_forecast = analyzer.get_weekly_forecast()
    print(f'✅ Weekly forecast with {len(weekly_forecast)} days')
    
except Exception as e:
    print(f'⚠️ Moon analyzer issue: {e}')

print('✅ Moon analyzer test complete')