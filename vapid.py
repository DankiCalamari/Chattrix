from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
import base64

def generate_vapid_keys():
    """Generate VAPID key pair for web push notifications"""
    
    # Generate private key
    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    
    # Get public key
    public_key = private_key.public_key()
    
    # Serialize private key
    private_key_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    # Serialize public key in uncompressed format
    public_key_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint
    )
    
    # Convert to base64 URL-safe format
    private_key_b64 = base64.urlsafe_b64encode(private_key_bytes).decode('utf-8').rstrip('=')
    public_key_b64 = base64.urlsafe_b64encode(public_key_bytes).decode('utf-8').rstrip('=')
    
    return {
        'private_key': private_key_b64,
        'public_key': public_key_b64
    }

if __name__ == "__main__":
    # Generate VAPID keys
    vapid_keys = generate_vapid_keys()
    
    # Write to file
    try:
        with open("vapid.txt", "w") as f:
            f.write(f"Private Key: {vapid_keys['private_key']}\n")
            f.write(f"Public Key: {vapid_keys['public_key']}\n")
        print("✅ VAPID keys saved to vapid.txt")
    except Exception as e:
        print(f"❌ Error writing to file: {e}")
    
    # Print to console
    print("\n🔑 Generated VAPID Keys:")
    print("=" * 50)
    print(f"Private Key: {vapid_keys['private_key']}")
    print(f"Public Key: {vapid_keys['public_key']}")
    print("=" * 50)
    
    # Provide instructions
    print("\n📝 Next Steps:")
    print("1. Copy these keys to your .env file:")
    print(f"   VAPID_PRIVATE_KEY={vapid_keys['private_key']}")
    print(f"   VAPID_PUBLIC_KEY={vapid_keys['public_key']}")
    print("\n2. Or update them directly in app.py if not using environment variables")
    print("\n3. Restart your application to use the new keys")