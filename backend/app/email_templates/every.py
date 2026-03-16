"""
Every — email templates.

All templates return rendered HTML strings.
Brand: clean white, minimal, text-forward. Black button. Every logo top-left.
"""

from typing import Optional


def _base_template(body_html: str, preheader: str = "", postscript: str = "") -> str:
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
{postscript}
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
    calendar_url = kwargs.get("calendar_url", "https://www.addevent.com/calendar/r7n3nkd1b7wm")

    subject = "Welcome to the Build Production-ready Apps course"

    ps = '<p style="margin:16px 0 0 0; font-size:13px; color:#666666;">P.S. We want you to be challenged, but never confused. If you have any questions, just reply to this email.</p>'

    body = f"""<p style="margin:0 0 16px 0;">Hey {first_name},</p>

<p style="margin:0 0 16px 0;">You\u2019re in. Welcome to <strong>Build Production-ready Apps</strong>.</p>

<p style="margin:0 0 16px 0;">Over two half-days on <strong>March 12\u201313</strong>, you\u2019ll go from prototype to production\u2014building and deploying a real, authenticated app with Claude Code. You\u2019ll leave with something live on the internet that you built yourself.</p>

<p style="margin:0 0 16px 0;">Here\u2019s what\u2019s waiting for you on <strong>March 12 and 13, from 12:30 p.m. to 5:00 p.m. Eastern Time</strong>:</p>

<p style="margin:0 0 16px 0;">You\u2019ll learn how to scaffold a full-stack project, ship it to a live URL, set up testing, and then use compound engineering to build features in parallel. Mike Taylor, Every\u2019s in-house expert practitioner, will guide you through every step, with guest appearances from Kieran Klaassen and Dan Shipper.</p>

<p style="margin:0 0 16px 0;">But this isn\u2019t just about building one app. You\u2019ll walk away with a repeatable workflow\u2014skills, sub-agents, worktrees\u2014you can apply to your own products, tools, side projects, and beyond.</p>

<p style="margin:0 0 8px 0;"><strong>Onboarding</strong></p>
<p style="margin:0 0 16px 0;">To get set up and make sure you\u2019re ready for the day, please complete this <a href="{onboarding_url}" style="color:#222222;">5-minute onboarding form</a> if you haven\u2019t done so yet.</p>

<p style="margin:0 0 16px 0;">Once you submit, you\u2019ll be officially enrolled and get access to our Circle community where you can connect with other participants and access resources before and after the course.</p>

<p style="margin:0 0 16px 0;">It only takes 5 minutes.</p>

{_button("Complete your onboarding form", onboarding_url)}

<p style="margin:0 0 8px 0;"><strong>Add the course to your calendar</strong></p>
<p style="margin:0 0 16px 0;">Click the button below to add the course to your calendar. The course runs 12:30\u20135:00 p.m. ET on both days.</p>

{_button("Add to my calendar", calendar_url)}

<p style="margin:0 0 8px 0;"><strong>A quick note on course fit</strong></p>
<p style="margin:0 0 16px 0;">This course assumes you\u2019ve already used Claude Code and built something with it\u2014even something small. We\u2019ll be moving fast from Day 1, and there won\u2019t be time to cover the basics, including Claude Code setup. If you\u2019re brand new to Claude Code and have never used it, this course will be tough to follow. Reply to this email and we\u2019ll help you figure out the right fit.</p>

<p style="margin:0 0 8px 0;"><strong>What\u2019s coming next</strong></p>
<p style="margin:0 0 16px 0;">Keep an eye on your inbox for further details as we get closer to the course date.</p>

<p style="margin:0 0 16px 0;">We\u2019re looking forward to seeing you on Thursday.</p>

"""

    html = _base_template(body, preheader="You\u2019re in \u2014 here\u2019s how to get ready for March 12\u201313", postscript=ps)
    return {"subject": subject, "html": html}


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
    """Welcome + get set up — Broadcast #1 (same body as onboarding confirmation, different subject)."""
    onboarding_url = kwargs.get("onboarding_form_url", "")
    if not onboarding_url and hasattr(product, "typeform_form_id") and product.typeform_form_id:
        onboarding_url = f"https://form.typeform.com/to/{product.typeform_form_id}"
    calendar_url = kwargs.get("calendar_url", "https://www.addevent.com/calendar/r7n3nkd1b7wm")

    subject = "Welcome to the Build Production-ready Apps course"

    ps = '<p style="margin:16px 0 0 0; font-size:13px; color:#666666;">P.S. We want you to be challenged, but never confused. If you have any questions, just reply to this email.</p>'

    body = f"""<p style="margin:0 0 16px 0;">Hey {first_name},</p>

<p style="margin:0 0 16px 0;">You\u2019re in. Welcome to <strong>Build Production-ready Apps</strong>.</p>

<p style="margin:0 0 16px 0;">Over two half-days on <strong>March 12\u201313</strong>, you\u2019ll go from prototype to production\u2014building and deploying a real, authenticated app with Claude Code. You\u2019ll leave with something live on the internet that you built yourself.</p>

<p style="margin:0 0 16px 0;">Here\u2019s what\u2019s waiting for you on <strong>March 12 and 13, from 12:30 p.m. to 5:00 p.m. Eastern Time</strong>:</p>

<p style="margin:0 0 16px 0;">You\u2019ll learn how to scaffold a full-stack project, ship it to a live URL, set up testing, and then use compound engineering to build features in parallel. Mike Taylor, Every\u2019s in-house expert practitioner, will guide you through every step, with guest appearances from Kieran Klaassen and Dan Shipper.</p>

<p style="margin:0 0 16px 0;">But this isn\u2019t just about building one app. You\u2019ll walk away with a repeatable workflow\u2014skills, sub-agents, worktrees\u2014you can apply to your own products, tools, side projects, and beyond.</p>

<p style="margin:0 0 8px 0;"><strong>Onboarding</strong></p>
<p style="margin:0 0 16px 0;">To get set up and make sure you\u2019re ready for the day, please complete this <a href="{onboarding_url}" style="color:#222222;">5-minute onboarding form</a> if you haven\u2019t done so yet.</p>

<p style="margin:0 0 16px 0;">Once you submit, you\u2019ll be officially enrolled and get access to our Circle community where you can connect with other participants and access resources before and after the course.</p>

<p style="margin:0 0 16px 0;">It only takes 5 minutes.</p>

{_button("Complete your onboarding form", onboarding_url)}

<p style="margin:0 0 8px 0;"><strong>Add the course to your calendar</strong></p>
<p style="margin:0 0 16px 0;">Click the button below to add the course to your calendar. The course runs 12:30\u20135:00 p.m. ET on both days.</p>

{_button("Add to my calendar", calendar_url)}

<p style="margin:0 0 8px 0;"><strong>A quick note on course fit</strong></p>
<p style="margin:0 0 16px 0;">This course assumes you\u2019ve already used Claude Code and built something with it\u2014even something small. We\u2019ll be moving fast from Day 1, and there won\u2019t be time to cover the basics, including Claude Code setup. If you\u2019re brand new to Claude Code and have never used it, this course will be tough to follow. Reply to this email and we\u2019ll help you figure out the right fit.</p>

<p style="margin:0 0 8px 0;"><strong>What\u2019s coming next</strong></p>
<p style="margin:0 0 16px 0;">Keep an eye on your inbox for further details as we get closer to the course date.</p>

<p style="margin:0 0 16px 0;">We\u2019re looking forward to seeing you on Thursday.</p>

"""

    html = _base_template(body, preheader="You\u2019re in \u2014 here\u2019s how to get ready for March 12\u201313", postscript=ps)
    return {"subject": subject, "html": html}


def _bpra_project_circle(first_name: str, product: object, **kwargs) -> dict:
    """Your project + Circle — Mar 9 broadcast."""
    subject = "Let\u2019s get you ready for Thursday"
    circle_url = kwargs.get("circle_url", "https://every-e29269.circle.so/c/welcome-5f3b53/")
    calendar_url = kwargs.get("calendar_url", "https://www.addevent.com/calendar/r7n3nkd1b7wm")

    body = f"""<p style="margin:0 0 16px 0;">Hey {first_name},</p>

<p style="margin:0 0 16px 0;">
    We\u2019re three days out from <strong>Build Production-Ready Apps</strong>, and we hope you\u2019re getting excited.
</p>

<p style="margin:0 0 16px 0;">
    By the end of day Friday, you\u2019ll have an app that\u2019s deployed to a live URL, has user authentication, connects to a real database, and runs automated tests on every push. Not a demo. Not a prototype. <strong>A real app</strong> with real infrastructure\u2014the kind of thing you\u2019d actually ship. That\u2019s what we mean by \u201cproduction-ready.\u201d
</p>

<p style="margin:0 0 16px 0;">
    Before Thursday rolls around, there\u2019s some prep work that\u2019ll make your two days smoother, more productive, and way more enjoyable.
</p>

<p style="margin:0 0 16px 0;">
    <strong>Spend some time using Claude Code, and upgrade to Anthropic Max</strong><br>
    We\u2019ll be using Claude Code extensively across both days. To avoid hitting token limits mid-session, you\u2019ll need an Anthropic Max plan\u2014the standard plan won\u2019t be enough for the volume of work we\u2019ll be doing. If you\u2019re on a free or standard plan, upgrade at claude.ai before Thursday. This is important\u2014running out of tokens during a build is no fun.
</p>

<p style="margin:0 0 16px 0;">
    <strong>Create a GitHub account</strong><br>
    You\u2019ll need a free GitHub account to follow along during the course. If you don\u2019t have one, sign up at github.com. Use your personal email\u2014no paid plan needed.
</p>

<p style="margin:0 0 16px 0;">
    <strong>Create a Vercel account</strong><br>
    We\u2019ll be deploying to Vercel during the course. Sign up for a free account at <a href="https://vercel.com" style="color:#0969da; text-decoration:underline;">vercel.com</a> and connect it to your GitHub account.
</p>

<p style="margin:0 0 16px 0;">
    <strong>Create a Neon account</strong><br>
    We\u2019re using Neon for our database. Create a free account at <a href="https://neon.tech" style="color:#0969da; text-decoration:underline;">neon.tech</a>.
</p>

<p style="margin:0 0 16px 0;">
    <strong>Join Circle</strong><br>
    We\u2019re using <a href="{circle_url}" style="color:#0969da; text-decoration:underline;">Circle</a> as our course community. Log in with your Every subscriber email\u2014no separate account needed. Introduce yourself, connect with other students, and ask questions before the day.
</p>

{_button("Join Circle", circle_url)}

<p style="margin:0 0 16px 0;">
    <strong>Add the course to your calendar</strong><br>
    The course runs 12:30\u20135:00 p.m. ET on both days.
</p>

{_button("Add the course to my calendar", calendar_url)}

<p style="margin:0 0 16px 0;">
    <strong>Complete your onboarding form</strong><br>
    If you haven\u2019t already, fill out the short onboarding form so we know a bit about you and what you\u2019re hoping to build. It only takes a few minutes.
</p>

{_button("Complete onboarding form", "https://form.typeform.com/to/YyHqtkye")}

<p style="margin:0 0 8px 0;"><strong style="font-size:16px;">How the two days work</strong></p>

<p style="margin:0 0 16px 0;">
    <strong>Day 1 is guided and hands-on.</strong> Everyone builds together\u2014a fully deployed, authenticated app with passing tests. You\u2019ll go from zero to a live URL in one afternoon.
</p>

<p style="margin:0 0 16px 0;">
    <strong>Day 2 is where your learning compounds.</strong> You\u2019ll learn advanced Claude Code tooling\u2014skills, sub-agents, worktrees\u2014and use them to add features to your project. The capstone exercise: your peers suggest features, and you build two of them simultaneously using parallel Claude Code sessions.
</p>

<p style="margin:0 0 8px 0;"><strong style="font-size:16px;">Start thinking about your project</strong></p>

<p style="margin:0 0 16px 0;">
    You\u2019ll work on a project that matters to you. Start thinking about what you\u2019d want to build. The best ideas come from personal pain points. What\u2019s one task or workflow that you do regularly that could be turned into a simple app?
</p>

<p style="margin:0 0 8px 0;"><strong style="font-size:16px;">A quick note on course fit</strong></p>

<p style="margin:0 0 16px 0;">
    This course assumes you\u2019ve already used Claude Code and built something with it\u2014even something small. We\u2019ll be moving fast from Day 1, and there won\u2019t be time to cover the basics, including Claude Code setup. If you\u2019re brand new to Claude Code and have never used it, this course will be tough to follow. Reply to this email and we\u2019ll help you figure out the right fit.
</p>

<p style="margin:0 0 0 0;">See you Thursday.</p>"""

    html = _base_template(body, preheader="Prep work for Build Production-Ready Apps")
    return {"subject": subject, "html": html}


def _bpra_tomorrow(first_name: str, product: object, **kwargs) -> dict:
    """Tomorrow — final checklist. Mar 11 broadcast."""
    subject = "Starts tomorrow\u2014Build Production-ready Apps"
    zoom_url = kwargs.get("zoom_url", "https://us06web.zoom.us/j/85417017675?pwd=uzMLsNsv2E36vddKtemaQuPOMm6XFR.1")
    circle_url = kwargs.get("circle_url", "https://every-e29269.circle.so/c/welcome-5f3b53/")
    calendar_url = kwargs.get("calendar_url", "https://www.addevent.com/calendar/r7n3nkd1b7wm")
    onboarding_url = kwargs.get("onboarding_url", "https://form.typeform.com/to/YyHqtkye")

    body = f"""<p style="margin:0 0 16px 0;">Hi {first_name},</p>

<p style="margin:0 0 16px 0;">
    <strong>Build Production-Ready Apps</strong> starts tomorrow\u2014we\u2019re looking forward to seeing you there at <strong>12:30 p.m. Eastern Time</strong>.
</p>

{_button("Join the Zoom session", zoom_url)}

<p style="margin:0 0 8px 0;"><strong>Here\u2019s your final checklist.</strong> Make sure you have:</p>

<ul style="margin:0 0 16px 0; padding-left:24px;">
    <li style="margin-bottom:8px;">Installed <a href="https://docs.anthropic.com/en/docs/claude-code/overview" target="_blank" style="color:#222222;">Claude Code</a> in the terminal</li>
    <li style="margin-bottom:8px;">An <a href="https://claude.com/pricing" target="_blank" style="color:#222222;">Anthropic Max plan</a> (so you don\u2019t hit token limits mid-session)</li>
    <li style="margin-bottom:8px;">A <a href="https://github.com" target="_blank" style="color:#222222;">GitHub account</a></li>
    <li style="margin-bottom:8px;">A <a href="https://vercel.com" target="_blank" style="color:#222222;">Vercel account</a> connected to GitHub</li>
    <li style="margin-bottom:8px;">A <a href="https://neon.tech" target="_blank" style="color:#222222;">Neon account</a></li>
    <li style="margin-bottom:8px;">Completed your <a href="{onboarding_url}" target="_blank" style="color:#222222;">onboarding form</a></li>
    <li style="margin-bottom:8px;"><a href="{calendar_url}" target="_blank" style="color:#222222;">Added the course to your calendar</a></li>
</ul>

<p style="margin:0 0 16px 0;">Join early if you can\u2014we\u2019ll be starting right on time.</p>

<p style="margin:0 0 4px 0;"><strong>A quick note on course fit</strong></p>
<p style="margin:0 0 16px 0;">This course assumes you\u2019ve already used Claude Code and built something with it\u2014even something small. We\u2019ll be moving fast from Day 1, and there won\u2019t be time to cover the basics, including Claude Code setup. If you\u2019re brand new to Claude Code and have never used it, this course will be tough to follow. If you think this course might not be a good fit, reply to this email and we\u2019ll help you figure out the right fit.</p>

<p style="margin:0 0 4px 0;"><strong>Questions?</strong></p>
<p style="margin:0 0 16px 0;">If you need any help, reply to this email or ask in <a href="{circle_url}" target="_blank" style="color:#222222;">Circle</a> and we\u2019ll get you sorted.</p>

<p style="margin:0 0 4px 0;"><strong>Can\u2019t make it?</strong></p>
<p style="margin:0 0 16px 0;">Life happens. If tomorrow no longer works for you, you can defer to a future course\u2014just let us know by replying to this email.</p>

<p style="margin:0 0 0 0;">See you tomorrow.</p>"""

    html = _base_template(body, preheader="Final checklist before we start")
    return {"subject": subject, "html": html}


def _bpra_thanks_survey(first_name: str, product: object, **kwargs) -> dict:
    """Thanks + completion survey — Mar 13 broadcast."""
    survey_url = kwargs.get("survey_url", "")
    if not survey_url and hasattr(product, "completion_survey_form_id") and product.completion_survey_form_id:
        survey_url = f"https://form.typeform.com/to/{product.completion_survey_form_id}"

    subject = "That's a wrap\u2014thanks for joining"

    body = f"""<p style="margin:0 0 16px 0;">Hey {first_name},</p>

<p style="margin:0 0 16px 0;">
    That's a wrap on <strong>Build Production-Ready Apps</strong>. Thanks for joining us. Over the last two days, you:
</p>

<ul style="margin:0 0 16px 0; padding-left:24px;">
    <li style="margin-bottom:6px;">Built and deployed a production-ready app to a live URL</li>
    <li style="margin-bottom:6px;">Set up authentication, a database, and a CI/CD pipeline</li>
    <li style="margin-bottom:6px;">Built two features in parallel from peer feedback</li>
    <li style="margin-bottom:6px;">And played with compound engineering</li>
</ul>

<p style="margin:0 0 16px 0;">
    That's no small thing. You showed up and shipped something real. Congrats!
</p>

<p style="margin:0 0 16px 0;">
    <strong>One quick ask:</strong> We'd love to hear how it went. Your feedback directly shapes how we run future courses\u2014and completing the survey unlocks your course recordings and a discount on future Every courses.
</p>

{_button("Complete My Course Reflection", survey_url)}

<p style="margin:0 0 16px 0;">
    It takes about 5 minutes. Once you complete the survey, you'll unlock access to the recordings\u2014these will be available from Monday 16th March.
</p>

<p style="margin:0 0 16px 0;">
    Thanks again for joining us.
</p>

"""

    html = _base_template(body, preheader="That's a wrap\u2014congratulations!")
    return {"subject": subject, "html": html}


def _bpra_survey_nudge(first_name: str, product: object, **kwargs) -> dict:
    """Survey nudge — Broadcast #5."""
    survey_url = kwargs.get("survey_url", "https://form.typeform.com/to/Y3LbPmdq")
    if not survey_url and hasattr(product, "completion_survey_form_id") and product.completion_survey_form_id:
        survey_url = f"https://form.typeform.com/to/{product.completion_survey_form_id}"

    subject = "Quick favour\u20145 minutes"

    body = f"""<p style="margin:0 0 16px 0;">Hey {first_name},</p>

<p style="margin:0 0 16px 0;">
    Thanks again for joining us for the <strong>Build Production-Ready Apps</strong> course.
</p>

<p style="margin:0 0 16px 0;">
    A gentle reminder to complete the course reflection. It should only take a few minutes, and your feedback is genuinely helpful!
</p>

{_button("Complete My Course Reflection", survey_url)}

<p style="margin:0 0 16px 0;">
    As a thank-you, everyone who completes the reflection gets access to the full set of course recordings and a discount code that can be used on a future course.
</p>

<p style="margin:0 0 16px 0;">
    Thanks again for joining us last week, and look forward to seeing you soon,
</p>

"""

    html = _base_template(body, preheader="Your feedback unlocks recordings + a discount")
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
# Scholarship Templates
# ---------------------------------------------------------------------------

def _scholarship_accepted(first_name: str, product: object, **kwargs) -> dict:
    """Scholarship acceptance — matches Google Doc copy."""
    discount_code = kwargs.get("discount_code", "")
    pay_amount = kwargs.get("pay_amount", "")
    checkout_url = kwargs.get("checkout_url", "")
    course_name = kwargs.get("course_name", "")
    if not course_name and hasattr(product, "product_name"):
        course_name = product.product_name

    subject = "Great news about your scholarship"

    body = f"""<p style="margin:0 0 16px 0;">Hey {first_name},</p>

<p style="margin:0 0 16px 0;">
    Great news\u2014you've been awarded a scholarship for {course_name}. We're excited to welcome you into the course.
</p>

<p style="margin:0 0 16px 0;">
    Your enrollment fee has been reduced to <strong>${pay_amount}</strong>. To claim your spot at this rate, use the code <strong>{discount_code}</strong> at <a href="{checkout_url}" style="color:#222222;">checkout</a>.
</p>

<p style="margin:0 0 16px 0;">
    If you have any questions, just reply to this email.
</p>

<p style="margin:0 0 16px 0;">
    Looking forward to seeing you there,
</p>

"""

    html = _base_template(body, preheader="Update on your scholarship application")
    return {"subject": subject, "html": html}


def _scholarship_rejected(first_name: str, product: object, **kwargs) -> dict:
    """Scholarship rejection — matches Google Doc copy."""
    course_name = kwargs.get("course_name", "")
    checkout_url = kwargs.get("checkout_url", "")
    if not course_name and hasattr(product, "product_name"):
        course_name = product.product_name

    subject = "Update on your scholarship application"

    enrollment_link = ""
    if checkout_url:
        enrollment_link = f'<a href="{checkout_url}" style="color:#222222;">enrollment is open</a>'
    else:
        enrollment_link = "enrollment is open"

    body = f"""<p style="margin:0 0 16px 0;">Hey {first_name},</p>

<p style="margin:0 0 16px 0;">
    Thanks for applying for a scholarship for {course_name}. We had a lot of applications this round, and unfortunately we weren't able to offer you a scholarship this time.
</p>

<p style="margin:0 0 16px 0;">
    We know that's not the news you were hoping for, and we appreciate you taking the time to apply.
</p>

<p style="margin:0 0 16px 0;">
    If you'd still like to join us, {enrollment_link} at the standard rate. And if cost is a barrier, keep an eye out for future courses\u2014we run scholarship rounds for each one.
</p>

<p style="margin:0 0 16px 0;">
    We'd love to have you there if it works out.
</p>

<p style="margin:0 0 16px 0;">
    All the best,
</p>

"""

    html = _base_template(body, preheader="Update on your scholarship application")
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
    "scholarship_accepted": _scholarship_accepted,
    "scholarship_rejected": _scholarship_rejected,
}
