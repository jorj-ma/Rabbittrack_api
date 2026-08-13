import os
import requests

POSTMARK_API_URL = "https://api.postmarkapp.com/email"


class EmailError(Exception):
    pass


def send_email(*, to: str, subject: str, html_body: str, text_body: str) -> None:
    token = os.environ.get("POSTMARK_SERVER_TOKEN")
    from_email = os.environ.get("POSTMARK_FROM_EMAIL")
    if not token or not from_email:
        raise EmailError("POSTMARK_SERVER_TOKEN / POSTMARK_FROM_EMAIL not configured.")

    response = requests.post(
        POSTMARK_API_URL,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Postmark-Server-Token": token,
        },
        json={
            "From": from_email,
            "To": to,
            "Subject": subject,
            "HtmlBody": html_body,
            "TextBody": text_body,
            "MessageStream": "outbound",
        },
        timeout=10,
    )
    if response.status_code != 200:
        raise EmailError(f"Postmark returned {response.status_code}: {response.text}")


def send_farm_invite_email(*, to: str, farm_name: str, farm_code: str, invite_token: str, role: str) -> None:
    base_url = os.environ.get("APP_BASE_URL", "http://localhost:5173")
    accept_url = f"{base_url}/accept-invite?token={invite_token}&email={to}"

    send_email(
        to=to,
        subject=f"You've been invited to join {farm_name} on RabbitTrack",
        html_body=(
            f"<p>You've been invited to join <strong>{farm_name}</strong> on RabbitTrack as a{'n' if role == 'admin' else ''} {role}.</p>"
            f"<p><a href=\"{accept_url}\">Click here to set up your account</a>.</p>"
            f"<p>Farm code: <strong>{farm_code}</strong> (you'll need this to sign in going forward).</p>"
            f"<p>This link expires in 7 days.</p>"
        ),
        text_body=(
            f"You've been invited to join {farm_name} on RabbitTrack as a {role}.\n\n"
            f"Set up your account: {accept_url}\n\n"
            f"Farm code: {farm_code} (you'll need this to sign in going forward).\n\n"
            f"This link expires in 7 days."
        ),
    )
