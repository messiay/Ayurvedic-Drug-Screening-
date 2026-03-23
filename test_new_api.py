import requests, json

BASE = "https://isa-papua-sharing-favor.trycloudflare.com"

# Test 1: SMILES to PDBQT with a real withanolide-like SMILES (Withaferin A, CID 265237)
smi = "CC(=O)O[C@@H]1[C@H](C)[C@@H]2CC[C@H]3[C@@H]4CC[C@H](O)[C@H]4CC[C@H]3[C@@]2(C)C[C@@H]1OC(=O)C=C"
print("=== Test 1: SMILES -> PDBQT (Withaferin A analog) ===")
r = requests.post(f"{BASE}/convert/smiles-to-pdbqt", json={"smiles": smi, "name": "withaferin_test"}, timeout=30)
resp = r.json()
content = resp.get("pdbqt_content", "")
atom_count = content.count("ATOM")
print(f"Status: {r.status_code}")
print(f"Atom count in PDBQT: {atom_count}")
print(f"Message: {resp.get('message', '')}")
print(content[:500])

# Test 2: A simpler glycosylated SMILES - glucose
print("\n=== Test 2: Glucose SMILES ===")
smi2 = "OC[C@H]1OC(O)[C@H](O)[C@@H](O)[C@@H]1O"
r2 = requests.post(f"{BASE}/convert/smiles-to-pdbqt", json={"smiles": smi2, "name": "glucose_test"}, timeout=30)
resp2 = r2.json()
content2 = resp2.get("pdbqt_content", "")
print(f"Atom count in PDBQT: {content2.count('ATOM')}")
print(f"Message: {resp2.get('message', '')}")
