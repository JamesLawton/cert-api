from fastapi import APIRouter

from controller.cert_issuer import sign_certificate

router = APIRouter()

router.include_router(sign_certificate.router, tags=["sign"])
