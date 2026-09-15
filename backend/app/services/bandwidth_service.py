import time
from typing import AsyncGenerator
from fastapi import Request, HTTPException, status
from fastapi.responses import StreamingResponse
from backend.app.core.config import settings


class BandwidthService:
    CHUNK_SIZE = 64 * 1024  # 64 KB chunks

    @classmethod
    def generate_controlled_stream(cls, size_mb: int) -> AsyncGenerator[bytes, None]:
        """
        Yields a stream of bytes amounting to exactly size_mb megabytes.
        """
        total_bytes = size_mb * 1024 * 1024
        bytes_sent = 0
        chunk = b"\x00" * cls.CHUNK_SIZE

        while bytes_sent < total_bytes:
            remaining = total_bytes - bytes_sent
            current_chunk = chunk if remaining >= cls.CHUNK_SIZE else chunk[:remaining]
            bytes_sent += len(current_chunk)
            yield current_chunk

    @classmethod
    def create_download_response(cls, requested_mb: int = None) -> StreamingResponse:
        """
        Creates a StreamingResponse with strict payload bounds.
        """
        if requested_mb is None or requested_mb <= 0:
            size_mb = settings.BANDWIDTH_TEST_SIZE_MB
        else:
            if requested_mb > settings.BANDWIDTH_TEST_SIZE_MB:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Requested size ({requested_mb}MB) exceeds configured maximum limit of {settings.BANDWIDTH_TEST_SIZE_MB}MB",
                )
            size_mb = requested_mb

        total_bytes = size_mb * 1024 * 1024

        response = StreamingResponse(
            cls.generate_controlled_stream(size_mb),
            media_type="application/octet-stream",
        )
        response.headers["Content-Length"] = str(total_bytes)
        response.headers["X-Bandwidth-Test-Size-MB"] = str(size_mb)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        return response

    @classmethod
    async def process_upload_test(cls, request: Request) -> dict:
        """
        Reads incoming stream up to max allowed upload size, measures elapsed time and calculates upload Mbps.
        """
        max_bytes = settings.BANDWIDTH_MAX_UPLOAD_MB * 1024 * 1024
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Payload exceeds maximum allowable upload size of {settings.BANDWIDTH_MAX_UPLOAD_MB}MB",
            )

        start_time = time.perf_counter()
        bytes_received = 0

        async for chunk in request.stream():
            bytes_received += len(chunk)
            if bytes_received > max_bytes:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Uploaded data exceeded limit of {settings.BANDWIDTH_MAX_UPLOAD_MB}MB",
                )

        elapsed_seconds = max(time.perf_counter() - start_time, 0.0001)
        duration_ms = round(elapsed_seconds * 1000, 2)
        bits = bytes_received * 8
        upload_mbps = round(bits / elapsed_seconds / 1_000_000, 2)

        return {
            "bytes_received": bytes_received,
            "duration_ms": duration_ms,
            "upload_mbps": upload_mbps,
            "message": "Observed bandwidth to Clipper-X test server",
        }
