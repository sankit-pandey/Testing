"""Story 5.3: round-trip extraction/reconstruction for each supported UI
resource format (Requirements §3.3).
"""
from app.services.resource_parser import detect_format, extract_strings, reconstruct


def test_detect_format():
    assert detect_format("strings.json") == "json"
    assert detect_format("messages.yaml") == "yaml"
    assert detect_format("messages.yml") == "yaml"
    assert detect_format("app.properties") == "properties"
    assert detect_format("strings.xml") == "xml"
    assert detect_format("Resources.resx") == "resx"


def test_json_round_trip():
    source = b'{"login": {"username": "Username", "password": "Password"}, "count": 3}'
    strings = extract_strings(source, "json")
    assert strings == {"login.username": "Username", "login.password": "Password"}

    translated = {k: v.upper() for k, v in strings.items()}
    result = reconstruct(source, "json", translated)
    import json

    data = json.loads(result)
    assert data["login"]["username"] == "USERNAME"
    assert data["count"] == 3  # non-string values untouched


def test_properties_round_trip():
    source = b"# comment\nusername=Username\npassword=Password\n"
    strings = extract_strings(source, "properties")
    assert strings == {"username": "Username", "password": "Password"}

    result = reconstruct(source, "properties", {"username": "Felhasznalonev"})
    text = result.decode("utf-8")
    assert "username=Felhasznalonev" in text
    assert "password=Password" in text
    assert "# comment" in text


def test_android_strings_xml_round_trip():
    source = b'<resources><string name="app_name">My App</string></resources>'
    strings = extract_strings(source, "xml")
    assert strings == {"app_name": "My App"}

    result = reconstruct(source, "xml", {"app_name": "Meine App"})
    assert b"Meine App" in result
