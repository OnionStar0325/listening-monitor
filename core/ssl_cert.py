from __future__ import annotations
import os
import datetime
import ipaddress
import logging
from pathlib import Path

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

import config

logger = logging.getLogger("listening_monitor.ssl")

def ensure_ssl_certificates() -> tuple[str, str]:
    """
    TLS/SSL 인증서(server.crt, server.key) 존재 여부를 확인하고,
    없을 경우 브라우저 호환성을 갖춘 자체 서명(Self-Signed) 인증서를 자동 생성합니다.
    (HTTPS 및 WSS 암호화 통신 필수 요구사항)
    """
    config.CERTS_DIR.mkdir(parents=True, exist_ok=True)
    
    cert_path = config.SSL_CERT_FILE
    key_path = config.SSL_KEY_FILE
    
    if cert_path.exists() and key_path.exists():
        logger.info(f"기존 SSL 인증서를 사용합니다: {cert_path}")
        return str(cert_path), str(key_path)
    
    logger.info("SSL 인증서가 없어 자체 서명(Self-Signed) 인증서를 신규 생성합니다...")
    
    # 2048-bit RSA 개인키 생성
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    
    # 인증서 주체(Subject) 및 발행자(Issuer) 정보
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "KR"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, config.SSL_ORGANIZATION),
        x509.NameAttribute(NameOID.COMMON_NAME, config.SSL_COMMON_NAME),
    ])
    
    # SAN (Subject Alternative Name) 구성: localhost, IP 주소 등
    alt_names = [
        x509.DNSName("localhost"),
        x509.DNSName("listening-monitor.local"),
        x509.DNSName("raspberrypi.local"),
        x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
    ]
    
    # 유효 기간: 10년 (임베디드 및 서버 환경 장기 운용 최적화)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow() - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=3650))
        .add_extension(
            x509.SubjectAlternativeName(alt_names),
            critical=False,
        )
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        )
        .sign(private_key, hashes.SHA256())
    )
    
    # 개인키 파일 저장 (chmod 600)
    with open(key_path, "wb") as f:
        f.write(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
    os.chmod(key_path, 0o600)
    
    # 인증서 파일 저장
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    
    logger.info(f"SSL 인증서 생성 완료: {cert_path}, {key_path}")
    return str(cert_path), str(key_path)
