"""
Script utilitaire pour réparer le fichier file_descriptions.json corrompu
"""
import json
import os
import sys
from pathlib import Path

DESCRIPTIONS_FILE = Path(__file__).parent / "file_descriptions.json"

def repair_json_file():
    """Répare un fichier JSON corrompu en extrayant les objets valides"""
    if not DESCRIPTIONS_FILE.exists():
        print(f"Fichier {DESCRIPTIONS_FILE} n'existe pas")
        return
    
    print(f"Tentative de réparation de {DESCRIPTIONS_FILE}...")
    
    # Lire le contenu
    with open(DESCRIPTIONS_FILE, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    
    if not content:
        print("Fichier vide, création d'un nouveau fichier vide")
        with open(DESCRIPTIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f, indent=4)
        return
    
    # Créer une sauvegarde
    backup_file = str(DESCRIPTIONS_FILE) + '.backup'
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Sauvegarde créée: {backup_file}")
    
    # Essayer de parser le fichier complet
    try:
        data = json.loads(content)
        if isinstance(data, list):
            print(f"✅ Fichier JSON valide! Contient {len(data)} entrées")
            return
    except json.JSONDecodeError as e:
        print(f"❌ Fichier JSON corrompu: {e}")
    
    # Méthode 1: Extraire toutes les entrées JSON valides ligne par ligne
    entries = []
    current_entry = ""
    brace_count = 0
    bracket_count = 0
    in_string = False
    escape_next = False
    
    for char in content:
        current_entry += char
        
        if escape_next:
            escape_next = False
            continue
        
        if char == '\\':
            escape_next = True
            continue
        
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
        
        if in_string:
            continue
        
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
        elif char == '[':
            bracket_count += 1
        elif char == ']':
            bracket_count -= 1
        
        # Si on ferme tous les objets/listes, on a un objet complet
        if brace_count == 0 and bracket_count == 0 and current_entry.strip():
            try:
                parsed = json.loads(current_entry.strip())
                if isinstance(parsed, dict):
                    entries.append(parsed)
                elif isinstance(parsed, list):
                    entries.extend(parsed)
                current_entry = ""
            except json.JSONDecodeError:
                # Essayer de trouver le dernier objet valide dans current_entry
                for i in range(len(current_entry), 0, -1):
                    try:
                        test = current_entry[:i].strip()
                        if test.endswith('}') or test.endswith(']'):
                            parsed = json.loads(test)
                            if isinstance(parsed, dict):
                                entries.append(parsed)
                            elif isinstance(parsed, list):
                                entries.extend(parsed)
                            current_entry = current_entry[i:]
                            break
                    except json.JSONDecodeError:
                        continue
    
    # Méthode 2: Si la méthode 1 échoue, essayer de trouver des patterns { ... }
    if not entries:
        import re
        # Chercher tous les objets JSON potentiels
        pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.finditer(pattern, content)
        for match in matches:
            try:
                parsed = json.loads(match.group())
                if isinstance(parsed, dict) and 'file_name' in parsed:
                    entries.append(parsed)
            except json.JSONDecodeError:
                continue
    
    # Dédupliquer par file_name
    seen = set()
    unique_entries = []
    for entry in entries:
        if isinstance(entry, dict) and 'file_name' in entry:
            file_name = entry['file_name']
            if file_name not in seen:
                seen.add(file_name)
                unique_entries.append(entry)
    
    print(f"✅ {len(unique_entries)} entrées valides trouvées")
    
    # Écrire le fichier réparé
    with open(DESCRIPTIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(unique_entries, f, indent=4, ensure_ascii=False)
    
    print(f"✅ Fichier réparé et sauvegardé!")

if __name__ == "__main__":
    repair_json_file()

