import numpy as np
import pandas as pd
from pathlib import Path

rng = np.random.default_rng(42)
OUT = Path("data/raw")
OUT.mkdir(parents=True, exist_ok=True)

N_CLAIMS = 6000
N_PATIENTS = 2500
START, END = pd.Timestamp("2025-01-01"), pd.Timestamp("2026-06-30")
SNAPSHOT = pd.Timestamp("2026-09-30")   # "today" for AR aging

# ---------- Dimensions ----------
PAYERS = {  # type, timely days, allowed %, share, pay days, auth_p, elig_p, info_p, mednec_p
    "Medicare":                  ("Medicare",   365, 0.38, 0.22, 14, 0.03, 0.010, 0.020, 0.05),
    "Medicaid TX":               ("Medicaid",    95, 0.30, 0.12, 35, 0.20, 0.060, 0.040, 0.06),
    "Aetna":                     ("Commercial", 120, 0.62, 0.14, 25, 0.20, 0.025, 0.020, 0.09),
    "Cigna":                     ("Commercial", 180, 0.60, 0.12, 22, 0.18, 0.020, 0.020, 0.08),
    "UnitedHealthcare":          ("Commercial",  90, 0.58, 0.20, 28, 0.25, 0.025, 0.025, 0.11),
    "Blue Cross Blue Shield TX": ("Commercial", 180, 0.65, 0.14, 24, 0.15, 0.020, 0.020, 0.07),
    "Humana":                    ("Commercial", 180, 0.55, 0.06, 30, 0.28, 0.030, 0.020, 0.10),
}
PROVIDERS = {
    "Dr. Sarah Mitchell": "Family Medicine", "Dr. James Carter": "Internal Medicine",
    "Dr. Priya Nair": "Orthopedics", "Dr. Michael Brooks": "Cardiology",
    "Dr. Emily Tran": "Dermatology", "Dr. David Okafor": "Gastroenterology",
}
# cpt: (description, illustrative charge, requires prior auth)
CPT = {
    "99213": ("Office visit, established, low-moderate", 135, False),
    "99214": ("Office visit, established, moderate-high", 195, False),
    "99203": ("Office visit, new patient, low", 190, False),
    "99204": ("Office visit, new patient, moderate", 290, False),
    "99395": ("Preventive visit, established, 18-39", 220, False),
    "93000": ("Electrocardiogram, complete", 65, False),
    "80053": ("Comprehensive metabolic panel", 40, False),
    "85025": ("Complete blood count with differential", 30, False),
    "36415": ("Venipuncture", 15, False),
    "71046": ("Chest X-ray, 2 views", 110, False),
    "73721": ("MRI lower extremity joint without contrast", 1200, True),
    "97110": ("Therapeutic exercise, 15 min", 95, True),
    "20610": ("Arthrocentesis, major joint", 210, False),
    "11102": ("Skin biopsy, single lesion", 260, False),
    "45378": ("Colonoscopy, diagnostic", 1400, False),
    "90471": ("Immunization administration", 45, False),
}
SPEC_CPT = {
    "Family Medicine":   ["99213","99214","99203","99395","36415","85025","80053","90471"],
    "Internal Medicine": ["99213","99214","99204","93000","80053","85025","36415","71046"],
    "Orthopedics":       ["99213","99204","73721","97110","20610","71046"],
    "Cardiology":        ["99214","99204","93000","71046"],
    "Dermatology":       ["99213","99203","11102"],
    "Gastroenterology":  ["99204","99214","45378"],
}
BUNDLE_PRONE = {"36415","93000","90471","20610"}
LAB_IMG = {"80053","85025","71046","73721"}
MED_NEC = {"73721","97110","45378"}

DENIALS = {  # code: (description, category, overturn probability)
    "CO-16":  ("Claim lacks information needed for adjudication", "Missing Information", 0.70),
    "CO-27":  ("Expenses incurred after coverage terminated",     "Eligibility",         0.15),
    "CO-22":  ("Care may be covered by another payer (COB)",      "Eligibility",         0.50),
    "CO-29":  ("Time limit for filing has expired",               "Timely Filing",       0.05),
    "CO-50":  ("Not deemed a medical necessity by the payer",     "Medical Necessity",   0.35),
    "CO-197": ("Precertification/authorization absent",           "Authorization",       0.25),
    "CO-4":   ("Procedure code inconsistent with modifier",       "Coding",              0.65),
    "CO-97":  ("Payment included in allowance for another service","Coding",             0.30),
    "CO-11":  ("Diagnosis inconsistent with procedure",           "Coding",              0.50),
}

dim_payer = pd.DataFrame({"payer_key": range(1, len(PAYERS)+1),
    "payer_name": list(PAYERS), "payer_type": [v[0] for v in PAYERS.values()],
    "timely_filing_days": [v[1] for v in PAYERS.values()]})
dim_provider = pd.DataFrame({"provider_key": range(1, len(PROVIDERS)+1),
    "provider_name": list(PROVIDERS), "specialty": list(PROVIDERS.values())})
dim_procedure = pd.DataFrame({"procedure_key": range(1, len(CPT)+1), "cpt_code": list(CPT),
    "description": [v[0] for v in CPT.values()], "base_charge": [v[1] for v in CPT.values()],
    "requires_prior_auth": [int(v[2]) for v in CPT.values()]})
dim_denial = pd.DataFrame({"carc_code": list(DENIALS),
    "description": [v[0] for v in DENIALS.values()], "denial_category": [v[1] for v in DENIALS.values()]})
dates = pd.date_range("2025-01-01", "2026-12-31")
dim_date = pd.DataFrame({"date_key": dates.strftime("%Y%m%d").astype(int), "full_date": dates.date,
    "year": dates.year, "quarter": dates.quarter, "month": dates.month, "month_name": dates.strftime("%B")})

# ---------- Claims ----------
pnames = list(PAYERS)
patient_payer = rng.choice(pnames, size=N_PATIENTS, p=[PAYERS[p][3] for p in pnames])
provs = list(PROVIDERS)

def pick_denial(pay, cpt, line_no, lag):
    t, tf, _, _, _, auth_p, elig_p, info_p, med_p = PAYERS[pay]
    if lag > tf:
        return "CO-29"
    c = []
    if CPT[cpt][2]: c.append(("CO-197", auth_p))
    c += [("CO-27", elig_p*0.7), ("CO-22", elig_p*0.3), ("CO-16", info_p), ("CO-4", 0.015)]
    if line_no > 1 and cpt in BUNDLE_PRONE: c.append(("CO-97", 0.15))
    if cpt in LAB_IMG: c.append(("CO-11", 0.04))
    if cpt in MED_NEC: c.append(("CO-50", med_p))
    u, cum = rng.random(), 0.0
    for code, p in c:
        cum += p
        if u < cum: return code
    return None

rows = []
span = (END - START).days
for i in range(1, N_CLAIMS + 1):
    pat = int(rng.integers(N_PATIENTS)); pay = patient_payer[pat]
    prov = provs[int(rng.integers(len(provs)))]
    dos = START + pd.Timedelta(days=int(rng.integers(span)))
    r = rng.random()
    lag = int(rng.integers(1,15) if r < .82 else rng.integers(15,61) if r < .95 else rng.integers(61,151))
    submit = dos + pd.Timedelta(days=lag)
    n = int(rng.choice([1,2,3], p=[.6,.3,.1]))
    cpts = rng.choice(SPEC_CPT[PROVIDERS[prov]], size=min(n, len(SPEC_CPT[PROVIDERS[prov]])), replace=False)
    for ln, cpt in enumerate(cpts, 1):
        billed = float(CPT[cpt][1])
        code = pick_denial(pay, cpt, ln, lag)
        pay_days = PAYERS[pay][4]
        row = dict(claim_id=f"CLM{i:06d}", patient_id=f"P{pat:05d}", payer_name=pay, provider_name=prov,
                   cpt_code=cpt, dos_date=dos, submit_date=submit, billed_amount=billed)
        def paid_amounts():
            allowed = round(billed * PAYERS[pay][2] * rng.uniform(.9, 1.1), 2)
            pr_pct = 0.0 if PAYERS[pay][0] == "Medicaid" else rng.choice([0, .1, .2], p=[.3, .4, .3])
            pr = round(allowed * pr_pct, 2)
            return allowed, round(allowed - pr, 2), pr
        if code is None:
            a, p, pr = paid_amounts()
            pdate = submit + pd.Timedelta(days=int(np.clip(rng.normal(pay_days, 7), 7, 75)))
            row.update(allowed_amount=a, paid_amount=p, patient_resp=pr, payment_date=pdate,
                       claim_status="Paid", carc_code=None, is_first_pass_paid=1)
        else:
            if rng.random() < DENIALS[code][2]:
                a, p, pr = paid_amounts()
                pdate = submit + pd.Timedelta(days=int(rng.integers(45, 121)))
                row.update(allowed_amount=a, paid_amount=p, patient_resp=pr, payment_date=pdate,
                           claim_status="Paid", carc_code=code, is_first_pass_paid=0)
            else:
                u = rng.random()
                st = "Appealed" if u < .30 else "Written-off" if u < .75 else "Denied"
                row.update(allowed_amount=0.0, paid_amount=0.0, patient_resp=0.0, payment_date=pd.NaT,
                           claim_status=st, carc_code=code, is_first_pass_paid=0)
        rows.append(row)

df = pd.DataFrame(rows)
clean_rows = len(df)

# ---------- Inject realistic mess ----------
log = {}
def pick(frac, seed): return df.sample(frac=frac, random_state=seed).index

# 1. inconsistent payer names
V = {"Blue Cross Blue Shield TX": ["BCBS TX","Blue Cross TX","BCBS of Texas","blue cross blue shield tx "],
     "UnitedHealthcare": ["United Healthcare","UHC","UNITED HEALTHCARE"], "Aetna": ["AETNA","Aetna Inc","aetna "],
     "Cigna": ["CIGNA","Cigna Healthcare"], "Humana": ["HUMANA","Humana Inc."],
     "Medicare": ["MEDICARE","Medicare Part B"], "Medicaid TX": ["TX Medicaid","Medicaid Texas","MEDICAID"]}
i = pick(.12, 1); df.loc[i, "payer_name"] = [str(rng.choice(V[x])) for x in df.loc[i, "payer_name"]]; log["payer name variants"] = len(i)
# 2. service date after submit date
i = pick(.008, 2); df.loc[i, "dos_date"] = df.loc[i, "submit_date"] + pd.Timedelta(days=5); log["dos after submit"] = len(i)
# 3. paid claims missing payment date
i = df[df.claim_status == "Paid"].sample(frac=.02, random_state=3).index; df.loc[i, "payment_date"] = pd.NaT; log["paid but no payment date"] = len(i)
# 4. paid > allowed
i = df[df.paid_amount > 0].sample(frac=.005, random_state=4).index; df.loc[i, "paid_amount"] = (df.loc[i, "allowed_amount"] * 1.5).round(2); log["paid > allowed"] = len(i)
# 5. missing patient id
i = pick(.005, 5); df.loc[i, "patient_id"] = None; log["missing patient_id"] = len(i)
# 6. CPT trailing spaces
i = pick(.03, 6); df.loc[i, "cpt_code"] = df.loc[i, "cpt_code"] + " "; log["cpt trailing space"] = len(i)
# 7. mixed date formats
for col in ["dos_date", "submit_date", "payment_date"]:
    df[col] = pd.to_datetime(df[col]).dt.strftime("%Y-%m-%d")
i = pick(.05, 7)
for col in ["dos_date", "submit_date", "payment_date"]:
    df.loc[i, col] = pd.to_datetime(df.loc[i, col]).dt.strftime("%m/%d/%Y")
log["US-format dates"] = len(i)
# 8. exact duplicate rows
dups = df.sample(frac=.015, random_state=8); log["duplicate rows"] = len(dups)
df = pd.concat([df, dups]).sample(frac=1, random_state=9).reset_index(drop=True)

df = df[["claim_id","patient_id","payer_name","provider_name","cpt_code","dos_date","submit_date","payment_date",
         "billed_amount","allowed_amount","paid_amount","patient_resp","claim_status","carc_code","is_first_pass_paid"]]

for name, d in [("claims", df), ("dim_payer", dim_payer), ("dim_provider", dim_provider),
                ("dim_procedure", dim_procedure), ("dim_denial_code", dim_denial), ("dim_date", dim_date)]:
    d.to_csv(OUT / f"{name}.csv", index=False)

print(f"claims.csv: {len(df)} rows ({clean_rows} before duplicates)")
print("Injected issues:", log)