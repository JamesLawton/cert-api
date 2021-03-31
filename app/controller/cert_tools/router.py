from fastapi import APIRouter

from controller.cert_tools import generate_unsigned_certificate, generate_pdf, generate_research_object_schema

router = APIRouter()

router.include_router(generate_unsigned_certificate.router)
router.include_router(generate_pdf.router)
router.include_router(generate_research_object_schema.router)