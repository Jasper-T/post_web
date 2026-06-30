from fastapi import APIRouter

from backend.app.schemas.dsetkit import (
    DsetkitConvertRequest,
    DsetkitEvaluateRequest,
    DsetkitEvaluateResponse,
    DsetkitPlotRequest,
    DsetkitPredConvertRequest,
    DsetkitRunResponse,
    DsetkitToolsResponse,
)
from backend.app.services.dsetkit import get_tools_payload, run_convert, run_evaluate, run_plot, run_pred_convert


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


@router.post("/convert/pred", response_model=DsetkitRunResponse)
def convert_pred_annotations(request: DsetkitPredConvertRequest) -> DsetkitRunResponse:
    return run_pred_convert(request)


@router.post("/evaluate", response_model=DsetkitEvaluateResponse)
def evaluate_dataset(request: DsetkitEvaluateRequest) -> DsetkitEvaluateResponse:
    return run_evaluate(request)
