# build FHIR bundle here
from fhir.resources.bundle import Bundle
from fhir.resources.patient import Patient
from fhir.resources.encounter import Encounter
from fhir.resources.condition import Condition
from fhir.resources.procedure import Procedure
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding

ICD_SYSTEM = "http://id.who.int/icd/release/11"

def cc(code:str, display:str, system:str=ICD_SYSTEM):
    return CodeableConcept.construct(coding=[Coding.construct(system=system, code=code, display=display)], text=display)

def build_bundle(req) -> Bundle:
    pat = Patient.construct(id=req.patient.id or "pat1", name=[{"text": req.patient.name}], gender=req.patient.gender, birthDate=req.patient.birthDate)
    enc = Encounter.construct(id="enc1", subject={"reference": f"Patient/{pat.id}"})

    entries = [{"resource": pat}, {"resource": enc}]
    for i, c in enumerate(getattr(req, "conditions", []) or []):
        cond = Condition.construct(id=f"cond{i}", subject={"reference": f"Patient/{pat.id}"}, code=cc(c.code, c.display))
        entries.append({"resource": cond})
    for j, p in enumerate(getattr(req, "procedures", []) or []):
        proc = Procedure.construct(id=f"proc{j}", subject={"reference": f"Patient/{pat.id}"}, code=cc(p.code, p.display))
        entries.append({"resource": proc})

    return Bundle.construct(type="collection", entry=entries)

def summarize_bundle(b: Bundle) -> dict:
    counts = {"Patient":0,"Encounter":0,"Condition":0,"Procedure":0}
    for e in b.entry or []:
        r = e.resource
        counts[type(r).__name__] = counts.get(type(r).__name__,0)+1
    return counts
