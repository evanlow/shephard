"""Suggested presets for the member deactivation-reason dropdown.

The UI must always allow free text in addition to these presets.
"""

DEACTIVATION_REASON_SUGGESTIONS = [
    "Moved overseas",
    "Transferred church",
    "Attends another service",
    "No longer attending",
    "Deceased",
    "Other",
]

# Maximum length enforced for remarks and deactivation_reason at the
# service layer. Keep aligned with the column lengths in app/models/member.py.
REMARKS_MAX_LENGTH = 500
