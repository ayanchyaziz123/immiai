from ..schemas.checklist import ChecklistItem, ChecklistResponse

CHECKLISTS: dict[str, list[dict]] = {
    "marriage green card": [
        {"item": "Form I-485 (Application to Register Permanent Residence)", "required": True},
        {"item": "Form I-864 (Affidavit of Support)", "required": True},
        {"item": "Form I-131 (Advance Parole)", "required": False, "notes": "If you plan to travel abroad during the process"},
        {"item": "Form I-765 (Employment Authorization)", "required": False, "notes": "Apply if you need work authorization while waiting"},
        {"item": "Valid passport (foreign national)", "required": True},
        {"item": "US citizen/LPR spouse's passport or proof of status", "required": True},
        {"item": "Birth certificate (with certified translation)", "required": True},
        {"item": "Marriage certificate (with certified translation)", "required": True},
        {"item": "2 passport-style photographs", "required": True},
        {"item": "Form I-693 (Medical Examination) by USCIS civil surgeon", "required": True},
        {"item": "Police clearance certificates from each country lived 6+ months", "required": True},
        {"item": "Evidence of bona fide marriage (joint bank statements, photos, lease)", "required": True},
        {"item": "Form I-130 approval notice (if already approved)", "required": True},
        {"item": "USCIS filing fee ($1,440 total for I-485 + biometrics)", "required": True},
    ],
    "h-1b": [
        {"item": "Form I-129 (Petition for Nonimmigrant Worker)", "required": True},
        {"item": "Labor Condition Application (LCA) certified by DOL", "required": True},
        {"item": "Employer support letter describing the specialty occupation", "required": True},
        {"item": "Degree credential evaluation (if foreign degree)", "required": True},
        {"item": "College transcripts and diplomas", "required": True},
        {"item": "Copies of all previous US visa stamps and I-94 records", "required": True},
        {"item": "Valid passport (at least 6 months validity)", "required": True},
        {"item": "Passport photos", "required": True},
        {"item": "DS-160 form (for consular processing)", "required": False, "notes": "Required if applying at a US consulate abroad"},
        {"item": "Premium processing fee (Form I-907, $2,805)", "required": False, "notes": "Optional — guarantees 15-business-day decision"},
    ],
    "asylum": [
        {"item": "Form I-589 (Application for Asylum and Withholding of Removal)", "required": True},
        {"item": "Personal statement describing persecution", "required": True},
        {"item": "Evidence of persecution (police reports, medical records, news articles)", "required": True},
        {"item": "Country condition reports (State Dept, Human Rights Watch, Amnesty International)", "required": True},
        {"item": "Passport and any travel documents", "required": True},
        {"item": "Birth certificate", "required": True},
        {"item": "Identity documents (national ID, driver's license)", "required": True},
        {"item": "Proof you entered the US within the last year (I-94, entry stamp)", "required": True, "notes": "Must apply within 1 year of arrival unless exception applies"},
        {"item": "Affidavits from witnesses or family members", "required": False},
        {"item": "Two passport-size photographs", "required": True},
        {"item": "No filing fee", "required": True, "notes": "Asylum applications have no USCIS filing fee"},
    ],
    "citizenship": [
        {"item": "Form N-400 (Application for Naturalization)", "required": True},
        {"item": "Copy of permanent resident card (front and back)", "required": True},
        {"item": "2 passport-style photographs", "required": True},
        {"item": "Travel history outside the US (trips 24+ hours) in past 5 years", "required": True},
        {"item": "Tax returns for past 5 years", "required": True},
        {"item": "Marriage certificate (if applying based on marriage to US citizen)", "required": False},
        {"item": "Divorce decrees (if previously married)", "required": False},
        {"item": "Filing fee: $760 ($640 + $85 biometrics), or $640 if 75+", "required": True},
        {"item": "Study for civics test (100 questions about US history and government)", "required": True},
        {"item": "Practice English reading, writing, and speaking", "required": True},
    ],
    "student f-1": [
        {"item": "Form I-20 from SEVP-certified US school", "required": True},
        {"item": "DS-160 online visa application form", "required": True},
        {"item": "Valid passport (at least 6 months validity beyond intended stay)", "required": True},
        {"item": "SEVIS fee payment receipt ($350)", "required": True},
        {"item": "Visa application fee payment ($185 MRV fee)", "required": True},
        {"item": "Proof of financial support (bank statements, sponsor letter)", "required": True},
        {"item": "Acceptance letter from US school", "required": True},
        {"item": "Academic transcripts and diplomas", "required": True},
        {"item": "English proficiency test scores (TOEFL, IELTS, Duolingo)", "required": False, "notes": "Required by most schools; not required by consulate"},
        {"item": "Ties to home country evidence (employment, property, family)", "required": True, "notes": "Prove you intend to return home after studies"},
        {"item": "2 passport-size photographs", "required": True},
    ],
}

_FALLBACK: list[dict] = [
    {"item": "Valid passport", "required": True},
    {"item": "Completed USCIS application form", "required": True},
    {"item": "Filing fee payment", "required": True},
    {"item": "2 passport-style photographs", "required": True},
    {"item": "Birth certificate (certified translation if not in English)", "required": True},
    {"item": "Identity documents", "required": True},
    {"item": "Consult an immigration attorney for your specific situation", "required": False, "notes": "Strongly recommended"},
]


class ChecklistService:
    def get_checklist(self, visa_type: str) -> ChecklistResponse:
        key = visa_type.lower().strip()
        items_data = next(
            (v for k, v in CHECKLISTS.items() if k in key or key in k),
            _FALLBACK,
        )
        return ChecklistResponse(
            visa_type=visa_type,
            items=[ChecklistItem(**item) for item in items_data],
        )

    def list_types(self) -> list[str]:
        return list(CHECKLISTS.keys())
