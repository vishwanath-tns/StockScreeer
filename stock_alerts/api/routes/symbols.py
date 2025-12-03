"""Symbol API endpoints."""

from typing import Optional, List

from fastapi import APIRouter, Query
from pydantic import BaseModel

from ...core.enums import AssetType
from ...services.symbol_service import SymbolService

router = APIRouter()


class SymbolResponse(BaseModel):
    """Symbol information response."""
    symbol: str
    yahoo_symbol: str
    name: Optional[str] = None
    asset_type: str
    exchange: Optional[str] = None


class PriceResponse(BaseModel):
    """Current price response."""
    symbol: str
    yahoo_symbol: str
    price: float
    prev_close: float
    change: float
    change_pct: float
    high: float
    low: float
    volume: int
    timestamp: str


@router.get("/symbols/search", response_model=List[SymbolResponse])
async def search_symbols(
    q: str = Query(..., min_length=1, description="Search query"),
    asset_type: Optional[AssetType] = None,
    limit: int = Query(20, ge=1, le=100),
):
    """Search for symbols."""
    service = SymbolService()
    
    results = service.search_symbols(q, asset_type, limit)
    
    return [
        SymbolResponse(
            symbol=r['symbol'],
            yahoo_symbol=r['yahoo_symbol'],
            name=r.get('name'),
            asset_type=r['asset_type'],
            exchange=r.get('exchange'),
        )
        for r in results
    ]


@router.get("/symbols/popular", response_model=List[SymbolResponse])
async def get_popular_symbols(
    asset_type: AssetType = Query(..., description="Asset type"),
):
    """Get popular symbols for an asset type."""
    service = SymbolService()
    
    results = service.get_popular_symbols(asset_type)
    
    return [
        SymbolResponse(
            symbol=r['symbol'],
            yahoo_symbol=r['yahoo_symbol'],
            name=r.get('name'),
            asset_type=r['asset_type'],
            exchange=r.get('exchange'),
        )
        for r in results
    ]


@router.get("/symbols/{symbol}/price", response_model=PriceResponse)
async def get_symbol_price(
    symbol: str,
    asset_type: AssetType = Query(..., description="Asset type"),
):
    """Get current price for a symbol."""
    from fastapi import HTTPException, status
    
    service = SymbolService()
    
    price_data = service.get_current_price(symbol, asset_type)
    
    if not price_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not fetch price for {symbol}",
        )
    
    return PriceResponse(
        symbol=price_data['symbol'],
        yahoo_symbol=price_data['yahoo_symbol'],
        price=price_data['price'],
        prev_close=price_data['prev_close'],
        change=price_data['change'],
        change_pct=price_data['change_pct'],
        high=price_data['high'],
        low=price_data['low'],
        volume=price_data['volume'],
        timestamp=price_data['timestamp'],
    )


@router.get("/symbols/{symbol}/validate")
async def validate_symbol(
    symbol: str,
    asset_type: AssetType = Query(..., description="Asset type"),
):
    """Validate if a symbol exists and is tradeable."""
    service = SymbolService()
    
    is_valid = service.validate_symbol(symbol, asset_type)
    yahoo_symbol = service.get_yahoo_symbol(symbol, asset_type)
    
    return {
        "symbol": symbol,
        "yahoo_symbol": yahoo_symbol,
        "asset_type": asset_type.value,
        "valid": is_valid,
    }


@router.get("/symbols/asset-types")
async def get_asset_types():
    """Get list of supported asset types."""
    return {
        "asset_types": [
            {"value": at.value, "name": at.name}
            for at in AssetType
        ]
    }


@router.get("/symbols/alert-conditions")
async def get_alert_conditions():
    """Get list of supported alert conditions."""
    from ...core.enums import AlertCondition, AlertType
    
    return {
        "conditions": [
            {"value": c.value, "name": c.name}
            for c in AlertCondition
        ],
        "alert_types": [
            {"value": t.value, "name": t.name}
            for t in AlertType
        ],
    }
