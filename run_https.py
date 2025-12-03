#!/usr/bin/env python3
"""Run FastAPI with HTTPS using self-signed certificate."""

import ssl
import uvicorn
from pathlib import Path

def create_self_signed_cert():
    """Create self-signed certificate for development."""
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        import datetime
        
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        # Create certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "MatterDocs"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.utcnow()
        ).not_valid_after(
            datetime.datetime.utcnow() + datetime.timedelta(days=365)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.IPAddress("127.0.0.1"),
            ]),
            critical=False,
        ).sign(private_key, hashes.SHA256())
        
        # Write certificate and key
        cert_path = Path("cert.pem")
        key_path = Path("key.pem")
        
        cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        key_path.write_bytes(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
        
        return str(cert_path), str(key_path)
        
    except ImportError:
        print("❌ cryptography package not installed")
        print("Run: pip install cryptography")
        return None, None

def run_https():
    """Run the app with HTTPS."""
    cert_file, key_file = create_self_signed_cert()
    
    if not cert_file:
        print("❌ Could not create certificates")
        return
    
    print("🚀 Starting MatterDocs with HTTPS...")
    print("📋 Manifest URL: https://localhost:8000/matterdocs-outlook-manifest.xml")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        ssl_keyfile=key_file,
        ssl_certfile=cert_file,
        reload=True
    )

if __name__ == "__main__":
    run_https()