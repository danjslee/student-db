"""
Every — email templates.

All templates return rendered HTML strings.
Brand: clean white, minimal, text-forward. Black button. Every logo top-left.
"""

from typing import Optional


def _base_template(body_html: str, preheader: str = "") -> str:
    """Wrap body content in Every-branded email shell."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Every</title>
<!--[if mso]>
<style>table,td {{font-family: Georgia, serif;}}</style>
<![endif]-->
</head>
<body style="margin:0; padding:0; background-color:#ffffff; font-family: Georgia, 'Times New Roman', serif; color:#222222; font-size:15px; line-height:1.65;">

<!-- Preheader (hidden preview text) -->
<div style="display:none; max-height:0; overflow:hidden; mso-hide:all;">
    {preheader}
</div>

<!-- Outer wrapper -->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#ffffff;">
<tr><td align="center" style="padding: 0 20px;">

<!-- Content area -->
<table role="presentation" width="480" cellpadding="0" cellspacing="0" style="background-color:#ffffff;">

<!-- Logo -->
<tr>
<td style="padding: 40px 0 32px 0;">
    <img src="https://every-student-db.fly.dev/static/images/every-logo.png" alt="Every" width="90" style="display:block; border:0;">
</td>
</tr>

<!-- Body -->
<tr>
<td style="padding: 0 0 40px 0;">
{body_html}

<p style="margin:24px 0 0 0;">\u2014The Every team</p>
</td>
</tr>

<!-- Footer divider -->
<tr>
<td style="padding: 0;">
    <div style="border-top: 1px solid #e5e5e5;"></div>
</td>
</tr>

<!-- Footer -->
<tr>
<td style="padding: 28px 0 40px 0;">
    <p style="margin:0; color:#aaaaaa; font-size:12px; line-height:1.5; font-family: Georgia, 'Times New Roman', serif;">
        This email was sent by Every.<br>
        Questions? Reply to this email and we'll get back to you.
    </p>
</td>
</tr>

</table>
<!-- /Content area -->

</td></tr>
</table>
<!-- /Outer wrapper -->

</body>
</html>"""


# ---------------------------------------------------------------------------
# Button helper
# ---------------------------------------------------------------------------

def _button(text: str, url: str) -> str:
    """Black CTA button, matching Every's style."""
    return f"""<table role="presentation" cellpadding="0" cellspacing="0" style="margin: 24px 0;">
<tr>
<td style="background-color:#222222; border-radius:4px;">
    <a href="{url}" target="_blank"
       style="display:inline-block; padding:12px 28px; color:#ffffff; font-family: Georgia, 'Times New Roman', serif; font-size:14px; font-weight:500; text-decoration:none; letter-spacing:0.3px;">
        {text}
    </a>
</td>
</tr>
</table>"""


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

def enrollment_confirmation(
    first_name: str,
    course_name: str,
    course_dates: str,
    course_time: str,
    onboarding_form_url: str,
) -> dict:
    """
    Sent after purchase. Confirms enrollment, directs to onboarding form.

    Returns dict with 'subject' and 'html'.
    """
    subject = f"You're in \u2014 welcome to {course_name}"

    body = f"""<p style="margin:0 0 16px 0;">Hey {first_name},</p>

<p style="margin:0 0 16px 0;">
    Your enrollment in <strong>{course_name}</strong> is confirmed. Your spot is reserved\u2014we're looking forward to working with you.
</p>

<p style="margin:0 0 16px 0;">
    The course runs {course_dates}, {course_time}, live via Zoom. Closer to the start date, you'll receive your calendar invite and preparation instructions.
</p>

<p style="margin:0 0 8px 0;">
    <strong>One thing to do now:</strong> complete the 5-minute onboarding form to secure your enrollment. We use this to personalise your experience.
</p>

{_button("Complete onboarding form", onboarding_form_url)}

"""

    html = _base_template(body, preheader="Welcome to " + course_name + " \u2014 complete your onboarding to secure your spot.")
    return {"subject": subject, "html": html}


# ---------------------------------------------------------------------------
# BPRA Templates
# ---------------------------------------------------------------------------

def _bpra_onboarding_confirmation(first_name: str, product: object, **kwargs) -> dict:
    """Enrollment confirmation — sent on purchase/enrollment."""
    onboarding_url = kwargs.get("onboarding_form_url", "")
    if not onboarding_url and hasattr(product, "typeform_form_id") and product.typeform_form_id:
        onboarding_url = f"https://form.typeform.com/to/{product.typeform_form_id}"

    return enrollment_confirmation(
        first_name=first_name,
        course_name=product.product_name,
        course_dates=str(product.course_start_date) if product.course_start_date else "March 12, 2026",
        course_time="12:00\u201313:30 pm ET",
        onboarding_form_url=onboarding_url,
    )


def _bpra_form_reminder(first_name: str, product: object, **kwargs) -> dict:
    """Reminder to complete onboarding form — sent 3 days post-enrollment if not done."""
    onboarding_url = kwargs.get("onboarding_form_url", "")
    if not onboarding_url and hasattr(product, "typeform_form_id") and product.typeform_form_id:
        onboarding_url = f"https://form.typeform.com/to/{product.typeform_form_id}"

    subject = f"Quick reminder \u2014 complete your {product.product_name} onboarding"

    body = f"""<p style="margin:0 0 16px 0;">Hey {first_name},</p>

<p style="margin:0 0 16px 0;">
    Just a quick nudge\u2014we haven't received your onboarding form yet for <strong>{product.product_name}</strong>.
</p>

<p style="margin:0 0 16px 0;">
    It takes about 5 minutes and helps us personalise your experience. We'd love to have it before the course kicks off.
</p>

{_button("Complete onboarding form", onboarding_url)}

"""

    html = _base_template(body, preheader="5 minutes to personalise your course experience")
    return {"subject": subject, "html": html}


def _bpra_welcome(first_name: str, product: object, **kwargs) -> dict:
    """Welcome + get set up — Mar 5 broadcast."""
    subject = f"Welcome to {product.product_name} \u2014 let's get you set up"
    circle_url = kwargs.get("circle_url", "https://community.every.to")

    body = f"""<p style="margin:0 0 16px 0;">Hey {first_name},</p>

<p style="margin:0 0 16px 0;">
    We're a week out from <strong>{product.product_name}</strong> and we're excited to have you.
</p>

<p style="margin:0 0 16px 0;">
    Here's what to do before we start:
</p>

<p style="margin:0 0 8px 0;"><strong>1. Join the community</strong></p>
<p style="margin:0 0 16px 0;">
    Head to Circle and introduce yourself. This is where you'll connect with your cohort, ask questions, and share your work.
</p>

{_button("Join the community", circle_url)}

<p style="margin:0 0 8px 0;"><strong>2. Check your calendar</strong></p>
<p style="margin:0 0 16px 0;">
    You should have a calendar invite for each live session. If you don't see it, reply to this email and we'll sort it out.
</p>

<p style="margin:0 0 8px 0;"><strong>3. Come with a project in mind</strong></p>
<p style="margin:0 0 16px 0;">
    The course is hands-on. You'll get the most out of it if you bring a real project\u2014something you're working on or want to build. It doesn't need to be polished.
</p>

"""

    html = _base_template(body, preheader="One week to go \u2014 here's how to prepare")
    return {"subject": subject, "html": html}


def _bpra_project_circle(first_name: str, product: object, **kwargs) -> dict:
    """Your project + Circle — Mar 9 broadcast."""
    subject = "Your project + how to use Circle"
    circle_url = kwargs.get("circle_url", "https://community.every.to")

    body = f"""<p style="margin:0 0 16px 0;">Hey {first_name},</p>

<p style="margin:0 0 16px 0;">
    Three days until we kick off. Two things to make sure you're ready:
</p>

<p style="margin:0 0 8px 0;"><strong>Pick your project</strong></p>
<p style="margin:0 0 16px 0;">
    You'll be working on a real project throughout the course. If you haven't picked one yet, now's the time. It can be anything\u2014a blog post, a workflow, a product feature, a personal experiment. The only requirement: it's something you actually care about.
</p>

<p style="margin:0 0 8px 0;"><strong>Introduce yourself in Circle</strong></p>
<p style="margin:0 0 16px 0;">
    Drop a quick intro in the community\u2014who you are, what you're working on, what you're hoping to get out of the course. It's a great way to find people with similar interests.
</p>

{_button("Go to Circle", circle_url)}

"""

    html = _base_template(body, preheader="Pick your project and say hello")
    return {"subject": subject, "html": html}


def _bpra_tomorrow(first_name: str, product: object, **kwargs) -> dict:
    """Tomorrow — final checklist. Mar 11 broadcast."""
    subject = f"{product.product_name} starts tomorrow"
    zoom_url = kwargs.get("zoom_url", "")

    body = f"""<p style="margin:0 0 16px 0;">Hey {first_name},</p>

<p style="margin:0 0 16px 0;">
    We start tomorrow. Here's your final checklist:
</p>

<p style="margin:0 0 8px 0;">\u2705 <strong>Calendar invite</strong> \u2014 check you've got it. Sessions are 12:00\u201313:30 pm ET.</p>
<p style="margin:0 0 8px 0;">\u2705 <strong>Zoom link</strong> \u2014 it's in your calendar invite. Test it if you haven't.</p>
<p style="margin:0 0 8px 0;">\u2705 <strong>Project idea</strong> \u2014 have something in mind, even if it's rough.</p>
<p style="margin:0 0 16px 0;">\u2705 <strong>Show up curious</strong> \u2014 that's the main thing.</p>

<p style="margin:0 0 16px 0;">
    See you tomorrow.
</p>

"""

    html = _base_template(body, preheader="Final checklist before we start")
    return {"subject": subject, "html": html}


def _bpra_thanks_survey(first_name: str, product: object, **kwargs) -> dict:
    """Thanks + completion survey — Mar 13 broadcast."""
    survey_url = kwargs.get("survey_url", "")
    if not survey_url and hasattr(product, "completion_survey_form_id") and product.completion_survey_form_id:
        survey_url = f"https://form.typeform.com/to/{product.completion_survey_form_id}"

    subject = f"Thanks for joining {product.product_name}"

    body = f"""<p style="margin:0 0 16px 0;">Hey {first_name},</p>

<p style="margin:0 0 16px 0;">
    Thanks for being part of <strong>{product.product_name}</strong>. We hope you got a lot out of it.
</p>

<p style="margin:0 0 16px 0;">
    We'd love your feedback\u2014it takes about 3 minutes and directly shapes how we run future courses.
</p>

{_button("Share your feedback", survey_url)}

<p style="margin:0 0 16px 0;">
    Your responses are genuinely useful to us. Thank you.
</p>

"""

    html = _base_template(body, preheader="We'd love your feedback \u2014 3 minutes")
    return {"subject": subject, "html": html}


def _bpra_survey_nudge(first_name: str, product: object, **kwargs) -> dict:
    """Survey nudge — Mar 18 broadcast."""
    survey_url = kwargs.get("survey_url", "")
    if not survey_url and hasattr(product, "completion_survey_form_id") and product.completion_survey_form_id:
        survey_url = f"https://form.typeform.com/to/{product.completion_survey_form_id}"

    subject = "Quick favour \u2014 2 minutes"

    body = f"""<p style="margin:0 0 16px 0;">Hey {first_name},</p>

<p style="margin:0 0 16px 0;">
    If you haven't had a chance yet\u2014we'd really appreciate your feedback on <strong>{product.product_name}</strong>. It takes about 2\u20133 minutes.
</p>

{_button("Share feedback", survey_url)}

<p style="margin:0 0 16px 0;">
    Every response helps us make the next cohort better. Thanks.
</p>

"""

    html = _base_template(body, preheader="Your feedback shapes the next cohort")
    return {"subject": subject, "html": html}


def _bpra_recording_discount(first_name: str, product: object, **kwargs) -> dict:
    """Recording + discount — triggered on survey completion."""
    recording_url = kwargs.get("recording_url", "")
    discount_code = kwargs.get("discount_code", "")
    discount_url = kwargs.get("discount_url", "")

    subject = f"Your {product.product_name} recording + a thank you"

    body = f"""<p style="margin:0 0 16px 0;">Hey {first_name},</p>

<p style="margin:0 0 16px 0;">
    Thanks for sharing your feedback\u2014it genuinely helps.
</p>

<p style="margin:0 0 16px 0;">
    As promised, here's your session recording:
</p>

{_button("Watch recording", recording_url) if recording_url else ""}

<p style="margin:0 0 16px 0;">
    And as a thank you, here's a discount code for any future Every course:
</p>

<p style="margin:0 0 16px 0; font-size:18px;">
    <strong>{discount_code}</strong>
</p>

{_button("Browse upcoming courses", discount_url) if discount_url else ""}

"""

    html = _base_template(body, preheader="Your recording and a thank-you discount")
    return {"subject": subject, "html": html}


def _bpra_deferred_invite(first_name: str, product: object, **kwargs) -> dict:
    """Deferred invite — manual trigger for late enrollees."""
    optin_url = kwargs.get("optin_url", "")

    subject = f"Your spot in {product.product_name}"

    body = f"""<p style="margin:0 0 16px 0;">Hey {first_name},</p>

<p style="margin:0 0 16px 0;">
    Good news\u2014your spot in <strong>{product.product_name}</strong> is confirmed.
</p>

<p style="margin:0 0 16px 0;">
    Click below to complete your enrollment and get set up:
</p>

{_button("Complete enrollment", optin_url)}

"""

    html = _base_template(body, preheader="Your spot is confirmed \u2014 complete your enrollment")
    return {"subject": subject, "html": html}


# ---------------------------------------------------------------------------
# Template Registry
# ---------------------------------------------------------------------------

TEMPLATE_REGISTRY = {
    "onboarding_confirmation": _bpra_onboarding_confirmation,
    "form_reminder": _bpra_form_reminder,
    "welcome": _bpra_welcome,
    "project_circle": _bpra_project_circle,
    "tomorrow": _bpra_tomorrow,
    "thanks_survey": _bpra_thanks_survey,
    "survey_nudge": _bpra_survey_nudge,
    "recording_discount": _bpra_recording_discount,
    "deferred_invite": _bpra_deferred_invite,
}
