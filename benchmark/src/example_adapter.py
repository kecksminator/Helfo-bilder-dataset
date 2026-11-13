"""Eksempel på adapter. Sett inn Clinaxias egne kall og feltmapping før bruk.

Denne filen er bevisst ikke koblet til en server eller tredjepart.
"""
def ocr_image(image_path):
    # Returner rå OCR-tekst fra bildet, ikke fasit eller ferdig journal.
    raise NotImplementedError("Koble til Clinaxias OCR-grensesnitt")

def interpret_text(text):
    # Kjør samme tolkning på OCR-tekst og fasittekst. Returner dette formatet:
    # {"fields": {"teeth": {"state": "known", "value": ["16"]}},
    #  "suggestions": [{"code": "101", "status": "review"}],
    #  "flags": ["eligibility_unverified"]}
    raise NotImplementedError("Koble til Clinaxias strukturerings- og HELFO-funksjoner")
