# open-pqc-inventory

Modeled After [Cryptoscope](https://research.ibm.com/publications/cryptoscope-analyzing-cryptographic-usages-in-modern-software)

## Results
Detection in open source JavaScript projects:
### https://github.com/juhoen/hybrid-crypto-js
```json
[
    {
        "file_name": "/Users/abrahambrege/dev/open-pqc-inventory/frontend/tmp/da6a5875-e246-4de3-a57e-490c88d653be/repo/lib/rsa.js",
        "line_number": null,
        "api_call": "publicKeyToPem(publicKey)",
        "algorithm": "RSA",
        "cryptographic_function": "key serialization",
        "mode": null,
        "key_size": null,
        "purpose": "Format RSA public key as PEM for transport or storage",
        "multiple_uses": true
    },
    {
        "file_name": "/Users/abrahambrege/dev/open-pqc-inventory/frontend/tmp/da6a5875-e246-4de3-a57e-490c88d653be/repo/src/index.js",
        "line_number": null,
        "api_call": "require('./rsa')",
        "algorithm": "RSA",
        "cryptographic_function": null,
        "mode": null,
        "key_size": null,
        "purpose": null,
        "multiple_uses": false
    },
    {
        "file_name": "/Users/abrahambrege/dev/open-pqc-inventory/frontend/tmp/da6a5875-e246-4de3-a57e-490c88d653be/repo/lib/index.js",
        "line_number": null,
        "api_call": "require('./rsa')",
        "algorithm": "RSA",
        "cryptographic_function": null,
        "mode": null,
        "key_size": null,
        "purpose": "Likely RSA cryptography: key generation, encryption, decryption, or signing (based on import)",
        "multiple_uses": false
    },
    {
        "file_name": "src/webpack.js",
        "line_number": null,
        "api_call": "RSA",
        "algorithm": "RSA",
        "cryptographic_function": null,
        "mode": null,
        "key_size": null,
        "purpose": null,
        "multiple_uses": false
    },
    {
        "file_name": "lib/constants.js",
        "line_number": null,
        "api_call": null,
        "algorithm": "AES-CBC",
        "cryptographic_function": null,
        "mode": "CBC",
        "key_size": null,
        "purpose": null,
        "multiple_uses": true
    },
    {
        "file_name": "src/constants.js",
        "line_number": null,
        "api_call": null,
        "algorithm": "AES",
        "cryptographic_function": null,
        "mode": "CBC",
        "key_size": null,
        "purpose": null,
        "multiple_uses": true
    },
    {
        "file_name": "test/test.js",
        "line_number": null,
        "api_call": "new RSA()",
        "algorithm": "RSA",
        "cryptographic_function": "keygen",
        "mode": null,
        "key_size": null,
        "purpose": "asymmetric key generation for public-key cryptography",
        "multiple_uses": true
    },
    {
        "file_name": "/Users/abrahambrege/dev/open-pqc-inventory/frontend/tmp/da6a5875-e246-4de3-a57e-490c88d653be/repo/src/rsa.js",
        "line_number": null,
        "api_call": "publicKeyToPem(publicKey)",
        "algorithm": "RSA",
        "cryptographic_function": "key encoding (public key to PEM)",
        "mode": null,
        "key_size": null,
        "purpose": "Convert RSA public key object to PEM format for distribution or storage.",
        "multiple_uses": true
    },
    {
        "file_name": "/Users/abrahambrege/dev/open-pqc-inventory/frontend/tmp/da6a5875-e246-4de3-a57e-490c88d653be/repo/lib/webpack.js",
        "line_number": null,
        "api_call": "require('./rsa')",
        "algorithm": "RSA",
        "cryptographic_function": null,
        "mode": null,
        "key_size": null,
        "purpose": "Imports RSA cryptographic module (purpose unclear from AST)",
        "multiple_uses": false
    },
    {
        "file_name": "src/crypt.js",
        "line_number": 204,
        "api_call": "forge.random.getBytesSync",
        "algorithm": null,
        "cryptographic_function": "keygen",
        "mode": null,
        "key_size": null,
        "purpose": "IV or key material generation",
        "multiple_uses": false
    },
    {
        "file_name": "lib/crypt.js",
        "line_number": null,
        "api_call": "privateKey.sign",
        "algorithm": "RSA",
        "cryptographic_function": "sign",
        "mode": null,
        "key_size": null,
        "purpose": "digital signature generation",
        "multiple_uses": true
    }
]
```

## Diagram
![Relational Diagram](assets/pqc-inventory.png)

## Future Improvements
- Extend langauge support (Python, C++, Java)
- Network Analyzer
- Filesystem Analyzer
- AST vs source file toggle
- Tests
- Error handling
- Expand regex's
- Start support for specific libraries