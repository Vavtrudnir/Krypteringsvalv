# Hemliga valvet - Säker filkryptering

Ett modernt, säkert filvalv byggt med Python och AES-256-GCM kryptering.

## Funktioner

- **🔐 Militärgrad kryptering**: AES-256-GCM med autentiserad kryptering
- **🛡️ Säker nyckelderivning**: Argon2id med anpassbara parametrar
- **⚛️ Atoma filoperationer**: Förhindrar datakorruption vid avbrott
- **🔒 Fillåsning**: Förhindrar samtidig åtkomst från flera processer
- **💾 Kompression**: Zlib-kompression för att spara utrymme
- **🖥️ Modern GUI**: CustomTkinter med mörkt tema
- **🌐 Plattformsoberoende**: Fungerar på Windows, macOS och Linux
- **🇸🇪 Svenskt gränssnitt**: Helt på svenska

## Installation

1. Se till att du har Python 3.11 eller högre installerat
2. Klona eller ladda ner projektet
3. Installera beroenden:

```bash
pip install -r requirements.txt
```

## Användning

### Starta applikationen

```bash
python main.py
```

### Skapa ett nytt valv

1. Starta applikationen
2. Ange ett starkt lösenord
3. Klicka på "Skapa nytt valv"
4. Välj var du vill spara valvfilen

### Öppna ett befintligt valv

1. Starta applikationen
2. Ange ditt lösenord
3. Klicka på "Lås upp valvet"
4. Välj din valvfil

### Hantera filer

- **Lägg till filer**: Klicka på "Lägg till fil" och välj en eller flera filer
- **Extrahera filer**: Markera filer och klicka på "Extrahera"
- **Ta bort filer**: Markera filer och klicka på "Ta bort"

## Säkerhet

### Krypteringsdetaljer

- **Algoritm**: AES-256-GCM
- **Nyckelderivning**: Argon2id
  - Minne: 512 MiB
  - Tid: 4 iterationer
  - Parallelism: 4 trådar
  - Salt: 16 slumpmässiga bytes
- **Nonce**: 12 slumpmässiga bytes per operation
- **Kompression**: Zlib före kryptering

### Filsäkerhet

- Atoma filskrivningar med `os.replace()`
- Exklusiv fillåsning med `portalocker`
- Sökvägsvalidering för att förhindra path traversal
- Header-integritet via AAD (Additional Authenticated Data)

### Binärt format

```
Header (38 bytes, okrypterad):
- Magic Bytes: "PYVAULT2"
- Version: uint16
- Salt: 16 bytes
- Argon2 parametrar: 12 bytes

Krypterad payload:
- Nonce: 12 bytes
- Ciphertext: Variabel längd
```

## Projektstruktur

```
├── assets/          # Ikoner (fallback genereras automatiskt)
├── core/
│   ├── crypto.py    # Kryptografiska operationer
│   ├── container.py # Filformat och I/O
│   └── vfs.py       # Virtuellt filsystem
├── ui/
│   ├── gui.py       # Huvudgränssnitt
│   └── async_ops.py # Bakgrundsoperationer
├── main.py          # Startpunkt
├── requirements.txt # Beroenden
└── README.md        # Denna fil
```

## Beroenden

- `cryptography>=41.0.0` - Kryptografiska primitiver
- `customtkinter>=5.2.0` - Modern GUI
- `argon2-cffi>=23.0.0` - Nyckelderivning
- `portalocker>=2.7.0` - Fillåsning
- `Pillow>=10.0.0` - Bildhantering

## Säkerhetsrekommendationer

1. **Använd starka lösenord**: Minst 12 tecken, blandat tecken
2. **Säkerhetskopiera valvfilen**: Förlorat lösenord = förlorade data
3. **Uppdatera regelbundet**: Håll programvaran uppdaterad
4. **Kör på betrodd dator**: Undvik publika datorer

## Troubleshooting

### "Missing required dependencies"
Installera beroenden med `pip install -r requirements.txt`

### "Failed to decrypt vault"
Kontrollera att du använder rätt lösenord. Valvfilen kan vara korrupt om den avbrutits under skrivning.

### "File not found"
Kontrollera att valvfilen existerar och att du har läsbehörighet.

## Licens

© 2025 Hemliga valvet. All rights reserved.

## Bidrag

Detta är ett privat projekt. Bidrag tas inte emot för närvarande.
