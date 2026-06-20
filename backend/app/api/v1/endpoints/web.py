from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent.parent.parent / "templates"))

VISA_TYPES = ["Any", "H-1B", "F-1", "Green Card", "Asylum", "Citizenship", "L-1", "O-1", "B-1/B-2", "J-1"]

LANGUAGES = [
    {"code": "English",    "label": "English"},
    {"code": "Spanish",    "label": "Español"},
    {"code": "Chinese",    "label": "中文"},
    {"code": "Hindi",      "label": "हिंदी"},
    {"code": "Arabic",     "label": "العربية"},
    {"code": "Portuguese", "label": "Português"},
    {"code": "Bangla",     "label": "বাংলা"},
    {"code": "Urdu",       "label": "اردو"},
]

DOC_TYPES = ["None", "RFE", "Denial", "Approval Notice", "I-94", "Other"]

QUICK_QUESTIONS = [
    "What documents do I need for a green card?",
    "How do I check my USCIS case status?",
    "What is the H-1B visa and who qualifies?",
    "How long does naturalization take?",
    "What happens if I get an RFE?",
    "Can I work while my green card is pending?",
]

CHECKLIST_VISA_TYPES = [
    {"key": "marriage green card", "label": "Marriage Green Card", "icon": "💍"},
    {"key": "h-1b",                "label": "H-1B Work Visa",      "icon": "💼"},
    {"key": "asylum",              "label": "Asylum",               "icon": "🛡️"},
    {"key": "citizenship",         "label": "Citizenship",          "icon": "🇺🇸"},
    {"key": "student f-1",         "label": "Student (F-1)",        "icon": "🎓"},
]

PROCESSING_TIMES = [
    {"form": "I-485 (Green Card)",        "typical": "8–24 months"},
    {"form": "I-130 (Family Petition)",   "typical": "12–24+ months"},
    {"form": "I-765 (Work Permit)",       "typical": "3–5 months"},
    {"form": "N-400 (Naturalization)",    "typical": "8–21 months"},
    {"form": "I-90 (Green Card Renewal)", "typical": "8–24 months"},
    {"form": "H-1B Petition",             "typical": "3–6 months (15 days premium)"},
    {"form": "I-539 (Change of Status)",  "typical": "6–12 months"},
]

TIPS = [
    "Your receipt number is on your I-797 Notice of Action, in the format EAC1234567890.",
    "Case status updates can take 24–48 hours to appear online after USCIS action.",
    "Sign up for email/text alerts at myaccount.uscis.gov to get notified automatically.",
    "Call the USCIS Contact Center at 1-800-375-5283 if your case exceeds published processing times.",
]


@router.get("/", response_class=HTMLResponse)
async def chat_page(request: Request):
    return templates.TemplateResponse("chat.html", {
        "request":        request,
        "active":         "chat",
        "visa_types":     VISA_TYPES,
        "languages":      LANGUAGES,
        "doc_types":      DOC_TYPES,
        "quick_questions": QUICK_QUESTIONS,
    })


@router.get("/checklist", response_class=HTMLResponse)
async def checklist_page(request: Request):
    return templates.TemplateResponse("checklist.html", {
        "request":    request,
        "active":     "checklist",
        "visa_types": CHECKLIST_VISA_TYPES,
    })


@router.get("/tracker", response_class=HTMLResponse)
async def tracker_page(request: Request):
    return templates.TemplateResponse("tracker.html", {
        "request":          request,
        "active":           "tracker",
        "processing_times": PROCESSING_TIMES,
        "tips":             TIPS,
    })
