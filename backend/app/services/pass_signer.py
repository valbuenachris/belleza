# ============================================================
# backend/app/services/pass_signer.py - Firma del .pkpass (PKCS#7)
# Apple exige que la última versión de un pase llegue FIRMADA: el
# dispositivo valida la firma CMS/PKCS#7 (schema DER) sobre el
# manifest.json. Aquí se genera esa firma con 'openssl cms -sign'
# usando el certificado del Pass Type ID + la clave privada + el
# certificado intermedio WWDR de Apple.
#
# Es OPCIONAL y best-effort: si no hay credenciales configuradas (o
# openssl no está en la imagen), el pase se construye sin firma como
# antes, pero se registra un warning claro para que el operador
# configure PASS_SIGNER_CERT_PATH / PASS_SIGNER_KEY_PATH /
# PASS_WWDR_CERT_PATH antes de producción.
# ============================================================

import logging
import os
import shutil
import subprocess
import tempfile
from typing import Optional

from ..config import settings

logger = logging.getLogger(__name__)

_warned = {"unconfigured": False, "missing_openssl": False, "missing_file": False}


def is_signing_configured() -> bool:
    """True si el operador configuró los tres archivos para firmar."""
    return bool(
        settings.PASS_SIGNER_CERT_PATH
        and settings.PASS_SIGNER_KEY_PATH
        and settings.PASS_WWDR_CERT_PATH
    )


def warn_if_unconfigured() -> None:
    """Warning únicamente-una-vez por proceso cuando no hay firma."""
    global _warned
    if _warned["unconfigured"]:
        return
    logger.warning(
        "[WALLET][PKPASS] Pase SIN firma (unsigned). Apple valida la firma "
        "CMS en producción y actualizaciones oficiales. Configura "
        "PASS_SIGNER_CERT_PATH (cert del Pass Type ID), PASS_SIGNER_KEY_PATH "
        "(clave privada PEM) y PASS_WWDR_CERT_PATH (cert WWDR) para firmar "
        "el .pkpass."
    )
    _warned["unconfigured"] = True


def sign_manifest(manifest_bytes: bytes) -> Optional[bytes]:
    """
    Firma manifest.json con PKCS#7/CMS (output DER) usando openssl.

    Equivalent to:
      openssl cms -sign -binary -in manifest.json \\
          -signer pass_cert.pem -inkey pass_key.pem \\
          -certfile WWDR.pem -outform DER -out signature

    Returns:
        bytes de la firma (DER) o None si no se pudo firmar.
    """
    if not is_signing_configured():
        warn_if_unconfigured()
        return None

    exe = shutil.which("openssl")
    if not exe:
        global _warned
        if not _warned["missing_openssl"]:
            logger.warning(
                "[WALLET][PKPASS] 'openssl' no disponible en la imagen del "
                "backend; no se puede firmar el pase."
            )
            _warned["missing_openssl"] = True
        return None

    signer_cert = settings.PASS_SIGNER_CERT_PATH
    signer_key = settings.PASS_SIGNER_KEY_PATH
    wwdr_cert = settings.PASS_WWDR_CERT_PATH
    for path in (signer_cert, signer_key, wwdr_cert):
        if not os.path.isfile(path):
            logger.warning(f"[WALLET][PKPASS] Archivo de firma no encontrado: {path}; pase sin firmar.")
            return None

    with tempfile.TemporaryDirectory(prefix="pkpass-sign-") as tmp:
        manifest_in = os.path.join(tmp, "manifest.json")
        signature_out = os.path.join(tmp, "signature")
        with open(manifest_in, "wb") as fh:
            fh.write(manifest_bytes)

        cmd = [
            exe,
            "cms",
            "-sign",
            "-binary",
            "-in", manifest_in,
            "-signer", signer_cert,
            "-inkey", signer_key,
            "-certfile", wwdr_cert,
            "-outform", "DER",
            "-out", signature_out,
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=30)
        except Exception as e:
            logger.warning(f"[WALLET][PKPASS] openssl cms -sign no pudo ejecutarse: {e}")
            return None

        if proc.returncode != 0:
            detail = proc.stderr.decode("utf-8", errors="replace")[:300]
            logger.warning(f"[WALLET][PKPASS] openssl cms -sign falló ({detail}); pase sin firmar.")
            return None

        if not os.path.isfile(signature_out):
            logger.warning("[WALLET][PKPASS] openssl no produjo la firma; pase sin firmar.")
            return None

        with open(signature_out, "rb") as fh:
            signature = fh.read()
        logger.info("[WALLET][PKPASS] Pase firmado con PKCS#7 (DER)")
        return signature