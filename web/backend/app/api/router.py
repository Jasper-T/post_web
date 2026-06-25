from fastapi import APIRouter

from backend.app.api.routes import dsetkit, field_schema, file_tree, file_upload, image_browser, pipeline_tester


api_router = APIRouter(prefix="/api")
api_router.include_router(file_tree.router)
api_router.include_router(file_upload.router)
api_router.include_router(dsetkit.router)
api_router.include_router(field_schema.router)
api_router.include_router(image_browser.router)
api_router.include_router(pipeline_tester.router)
