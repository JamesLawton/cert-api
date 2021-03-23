from fastapi import APIRouter

from controller.cert_tools import generate_unsigned_certificate, generate_pdf

router = APIRouter()

router.include_router(generate_unsigned_certificate.router)
router.include_router(generate_pdf.router)