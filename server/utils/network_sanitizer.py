import re

def clean_output(raw_bytes: bytes) -> str:
    """
    Nettoie les octets bruts SSH en supprimant les séquences d'échappement ANSI,
    les caractères de retour arrière (backspace) et les invites de pagination diverses.
    """
    raw_str = raw_bytes.decode('utf-8', errors='replace')
    
    # Nettoyage des séquences ANSI (couleurs, positionnement du curseur)
    ansi_escape = re.compile(r'(?:\x1B[@-_][0-?]*[ -/]*[@-~])')
    clean_str = ansi_escape.sub('', raw_str)
    
    # Ciblage spécifique de la pagination Aruba/HP (ex: [24;1H)
    clean_str = re.sub(r'\[\d+;\d+H', '', clean_str)
    clean_str = re.sub(r'\[\?\d+h', '', clean_str)
    
    # Suppression des backspaces multiples et des caractères les précédant
    while '\x08' in clean_str:
        clean_str = re.sub(r'[^\x08]\x08', '', clean_str)
        
    # Suppression des reliquats de pagination dans le texte capturé
    clean_str = re.sub(r'-- MORE --, next page: Space, next line: Enter, quit: Control-C', '', clean_str, flags=re.IGNORECASE)
    clean_str = re.sub(r'--More--', '', clean_str, flags=re.IGNORECASE)
    
    # Trim final pour éviter les doubles sauts de ligne excessifs
    clean_str = re.sub(r'\n\s*\n', '\n\n', clean_str)
    
    return clean_str.strip()
