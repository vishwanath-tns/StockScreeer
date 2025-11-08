import json
from decimal import Decimal
from datetime import datetime

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import scanner_api


def make_ohlcv_df():
    idx = pd.date_range(end=pd.Timestamp('2025-10-28'), periods=5, freq='B')
    df = pd.DataFrame({
        'Open': [Decimal('100.0'), Decimal('101.0'), Decimal('102.0'), Decimal('103.0'), Decimal('104.0')],
        'High': [Decimal('110.0')] * 5,
        'Low': [Decimal('90.0')] * 5,
        'Close': [Decimal('105.0')] * 5,
        'Volume': [1000, 2000, 1500, 1200, 1300],
        'turnover_lacs': [Decimal('10.5')] * 5,
    }, index=idx)
    return df


def make_rsi_df():
    idx = pd.date_range(end=pd.Timestamp('2025-10-28'), periods=5, freq='B')
    df = pd.DataFrame({'rsi': [Decimal('55.5'), Decimal('56.0'), Decimal('57.0'), Decimal('58.0'), Decimal('59.0')]}, index=idx)
    return df


def make_fractal_df():
    idx = pd.date_range(end=pd.Timestamp('2025-10-28'), periods=3, freq='B')
    df = pd.DataFrame({'symbol': ['SBIN', 'RELI', 'TCS'], 'signal': ['buy', 'sell', 'buy']}, index=idx)
    return df


client = TestClient(scanner_api.app)


def test_ohlcv_endpoint_returns_data(monkeypatch):
    ohlcv = make_ohlcv_df()
    rsi = make_rsi_df()

    def mock_fetch(symbol, days=None):
        return ohlcv, rsi

    # patch the attribute on the imported module
    monkeypatch.setattr(scanner_api, 'fetch_price_and_rsi', mock_fetch)

    resp = client.get('/api/ohlcv', params={'symbol': 'SBIN', 'days': 5})
    assert resp.status_code == 200
    body = resp.json()
    assert body['symbol'] == 'SBIN'
    assert isinstance(body['data'], list)
    assert len(body['data']) == 5
    first = body['data'][0]
    # dates should be present as strings and numeric types normalized
    assert 'date' in first
    assert isinstance(first.get('Open'), (int, float)) or isinstance(first.get('Open'), (str,))


def test_rsi_endpoint_returns_data(monkeypatch):
    ohlcv = make_ohlcv_df()
    rsi = make_rsi_df()

    def mock_fetch(symbol, days=None):
        return ohlcv, rsi

    monkeypatch.setattr(scanner_api, 'fetch_price_and_rsi', mock_fetch)
    resp = client.get('/api/rsi', params={'symbol': 'SBIN', 'period': 14, 'days': 5})
    assert resp.status_code == 200
    body = resp.json()
    assert body['symbol'] == 'SBIN'
    assert isinstance(body['data'], list)
    # check rsi exists in first row
    if body['data']:
        assert 'rsi' in body['data'][0]


def test_fractal_breaks_endpoint_returns_data(monkeypatch):
    df = make_fractal_df()

    def mock_scan():
        return df

    monkeypatch.setattr(scanner_api, 'scan_fractal_breaks', mock_scan)
    resp = client.get('/api/fractal_breaks')
    assert resp.status_code == 200
    body = resp.json()
    assert 'data' in body
    assert isinstance(body['data'], list)
    assert len(body['data']) == 3
