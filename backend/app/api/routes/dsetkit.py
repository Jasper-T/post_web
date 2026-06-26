from fastapi import APIRouter

from backend.app.schemas.dsetkit import (
    DsetkitConvertRequest,
    DsetkitPlotRequest,
    DsetkitRunResponse,
    DsetkitToolsResponse,
)
from backend.app.services.dsetkit import get_tools_payload, run_convert, run_plot


router = APIRouter(prefix="/dsetkit", tags=["dsetkit"])


@router.get("/tools", response_model=DsetkitToolsResponse)
def read_tools() -> DsetkitToolsResponse:
    return DsetkitToolsResponse(**get_tools_payload())


@router.post("/convert", response_model=DsetkitRunResponse)
def convert_dataset(request: DsetkitConvertRequest) -> DsetkitRunResponse:
    return run_convert(request)


@router.post("/plot", response_model=DsetkitRunResponse)
def plot_dataset(request: DsetkitPlotRequest) -> DsetkitRunResponse:
    return run_plot(request)
