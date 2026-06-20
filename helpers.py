from datetime import datetime

def normalize_component_text(text: str) -> str:
    """
    Convert to CAPITAL and replace spaces with underscores.
    Example: resistor 10k -> RESISTOR_10K
    """
    if text is None:
        return ""
    text = str(text).strip().upper()
    text = "_".join(text.split())
    return text

def display_component_text(text: str) -> str:
    """
    Convert RESISTOR_10K -> Resistor 10k
    """
    if not text:
        return ""
    text = text.replace("_", " ").strip().lower()
    return text.title()

def build_component_key(component_name: str, part_number: str) -> str:
    component_name = normalize_component_text(component_name)
    part_number = normalize_component_text(part_number)
    return f"{component_name}__{part_number}"

def now_iso():
    return datetime.now().isoformat()

def today_str():
    return datetime.now().strftime("%Y-%m-%d")
