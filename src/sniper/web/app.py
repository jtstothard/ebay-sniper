"""FastAPI web application for eBay Sniper"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from ..config import config
from ..core.auth import AuthManager
from ..core.db import WatchStore
from ..core.ebay_client import eBayClient
from ..core.ntp import NTPSync
from ..core.sniper import SniperEngine
from ..scheduler import SniperScheduler

logger = logging.getLogger(__name__)


# Pydantic models
class WatchRequest(BaseModel):
    item_id: str
    max_bid: float
    source: Optional[str] = "api"


class SearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 20


class CancelRequest(BaseModel):
    watch_id: str


def create_app(
    db: WatchStore,
    sniper: SniperEngine,
    scheduler: SniperScheduler,
    ebay_client: eBayClient,
    ntp: NTPSync,
) -> FastAPI:
    """Create FastAPI application"""

    app = FastAPI(
        title="eBay Sniper Service",
        description="Self-hosted auction sniping for eBay",
        version="0.1.0",
    )

    # Templates
    templates = Jinja2Templates(directory="src/sniper/web/templates")

    # API Routes

    @app.get("/api/watches")
    async def list_watches_api(status: Optional[str] = None):
        """List all watches"""
        watches = sniper.list_watches(status)
        return {"watches": watches}

    @app.post("/api/watches")
    async def add_watch_api(request: WatchRequest):
        """Add a new watch"""
        try:
            watch = await sniper.add_watch(
                item_id=request.item_id,
                max_bid=request.max_bid,
                source=request.source or "api",
            )

            # Schedule the snipe
            scheduler.schedule_watch(watch["id"], watch["auction_end_time"])

            return watch
        except Exception as e:
            logger.error(f"Failed to add watch: {e}")
            raise HTTPException(status_code=400, detail=str(e))

    @app.get("/api/watches/{watch_id}")
    async def get_watch_api(watch_id: str):
        """Get a single watch"""
        watch = sniper.get_watch(watch_id)
        if not watch:
            raise HTTPException(status_code=404, detail="Watch not found")
        return watch

    @app.delete("/api/watches/{watch_id}")
    async def cancel_watch_api(watch_id: str):
        """Cancel a watch"""
        success = await sniper.cancel_watch(watch_id)
        if not success:
            raise HTTPException(status_code=404, detail="Watch not found or not active")

        # Unschedule the watch
        scheduler.unschedule_watch(watch_id)

        return {"success": True}

    @app.get("/api/watches/{watch_id}/log")
    async def get_watch_log_api(watch_id: str):
        """Get bid log for a watch"""
        watch = sniper.get_watch(watch_id)
        if not watch:
            raise HTTPException(status_code=404, detail="Watch not found")

        log = db.get_bid_log(watch_id)
        return {"watch_id": watch_id, "log": log}

    @app.get("/api/search")
    async def search_api(q: str, limit: int = 20):
        """Search eBay auctions"""
        try:
            results = await ebay_client.search_auctions(q, limit)
            return {"query": q, "results": results}
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/status")
    async def status_api():
        """Get service status"""
        now = ntp.get_adjusted_time()
        return {
            "status": "running",
            "environment": config.EBAY_ENVIRONMENT,
            "ntp_synced": ntp.synced,
            "ntp_offset": ntp.offset,
            "current_time": now.isoformat(),
            "bid_placement_stubbed": config.BID_PLACEMENT_STUBBED,
        }

    # Web Dashboard Routes

    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard(request: Request):
        """Web dashboard"""
        watches = sniper.list_watches("active")
        scheduled_jobs = scheduler.get_scheduled_jobs()
        status = await status_api()

        # Calculate time remaining for each watch
        for watch in watches:
            end_time = datetime.fromisoformat(watch["auction_end_time"])
            current_time = datetime.fromisoformat(status["current_time"])
            remaining = end_time - current_time
            watch["time_remaining"] = remaining.total_seconds()

        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {
                "watches": watches,
                "jobs": scheduled_jobs,
                "status": status,
            },
        )

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        """Redirect to dashboard"""
        return RedirectResponse(url="/dashboard")

    return app
