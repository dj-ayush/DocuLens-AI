import uvicorn

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from server.api.routes import router
from server.api.schemas import StandardAPIResponse
from server.core.vector_database import initialize_empty_vectorstores
from server.utils.logger import logger


app = FastAPI(
    title="DocuLens AI",
    description="Chat with one PDF",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://doculens-theta.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    logger.warning(
        f"Request validation failed for {request.url.path}"
    )

    return JSONResponse(
        status_code=422,
        content=StandardAPIResponse(
            status="error",
            message="Invalid request.",
        ).model_dump(),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request,
    exc: HTTPException,
):
    return JSONResponse(
        status_code=exc.status_code,
        content=StandardAPIResponse(
            status="error",
            message=str(exc.detail),
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
):
    logger.exception(
        f"Unhandled error for {request.url.path}"
    )

    return JSONResponse(
        status_code=500,
        content=StandardAPIResponse(
            status="error",
            message="Internal server error.",
        ).model_dump(),
    )


@app.on_event("startup")
async def startup_event():
    logger.info("Starting up app...")
    initialize_empty_vectorstores()
    logger.info("Startup complete.")


if __name__ == "__main__":
    logger.info("Running app...")

    uvicorn.run(
        "server.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )