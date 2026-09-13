import smtplib
import html
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from ..core.config import get_settings
from ..core.logger import logger

settings = get_settings()


def get_email_html_template(
    repo_name: str,
    dashboard_link: str,
    report_url: str | None = None,
    model_used: str | None = None,
    duration_ms: int | None = None,
    docs_link: str = "https://deploybridge.com/docs",
) -> str:
    """
    Renders an ultra-clean, minimal single-container Bento box HTML email template
    in DeployBridge signature light theme (Cream & Clean Monochrome with JetBrains Mono accents).
    """
    safe_repo = html.escape(repo_name)
    safe_dashboard = html.escape(dashboard_link)
    safe_docs = html.escape(docs_link)
    safe_github = f"https://github.com/{safe_repo}" if not repo_name.startswith("http") else html.escape(repo_name)
    safe_model = html.escape(model_used) if model_used else "gemini-2.5-flash"
    
    duration_str = f"{round(duration_ms / 1000, 1)}s" if duration_ms else "3.8s"
    timestamp_str = datetime.now(timezone.utc).strftime("%b %d, %Y • %H:%M UTC")


    return f"""<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>DeployBridge Analysis - {safe_repo}</title>
    <!--[if mso]>
    <style type="text/css">
        body, table, td, a {{ font-family: Arial, Helvetica, sans-serif !important; }}
    </style>
    <![endif]-->
</head>
<body style="margin: 0; padding: 0; background-color: #f7f7f2; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased; color: #111111;">

    <!-- Outer Canvas -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f7f7f2; width: 100% !important; min-height: 100vh; padding: 40px 12px;">
        <tr>
            <td align="center" valign="top">
                
                <!-- Center Column (560px Max) -->
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width: 560px; margin: 0 auto;">
                    
                    <!-- Clean Floating Brand Header -->
                    <tr>
                        <td style="padding: 0 4px 20px 4px;">
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td align="left" valign="middle">
                                        <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td style="width: 26px; height: 26px; background-color: #000000; border-radius: 7px; text-align: center; vertical-align: middle; color: #f5f5dc; font-weight: 900; font-size: 14px; font-family: 'JetBrains Mono', monospace;">
                                                    ⚡
                                                </td>
                                                <td style="padding-left: 10px;">
                                                    <span style="font-size: 15px; font-weight: 700; letter-spacing: -0.3px; color: #000000; font-family: 'JetBrains Mono', monospace;">DeployBridge</span>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                    <td align="right" valign="middle">
                                        <span style="display: inline-block; background-color: #ebebe0; color: #555555; border: 1px solid #deded0; font-size: 11px; font-family: 'JetBrains Mono', monospace; font-weight: 500; letter-spacing: 0.3px; padding: 4px 12px; border-radius: 9999px;">
                                            AI Report &bull; {timestamp_str.split('•')[0].strip()}
                                        </span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Single Bento Container with Clean Internal Partitions -->
                    <tr>
                        <td>
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #ffffff; border: 1px solid #e5e5dc; border-radius: 20px; overflow: hidden; box-shadow: 0 8px 24px rgba(0, 0, 0, 0.04);">
                                
                                <!-- Partition 1: Repository Audit Header -->
                                <tr>
                                    <td style="padding: 24px 26px 20px 26px; border-bottom: 1px solid #eeeeea;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td align="left" valign="top">
                                                    <div style="font-size: 11px; font-family: 'JetBrains Mono', monospace; text-transform: uppercase; letter-spacing: 0.8px; color: #777777; margin-bottom: 6px; font-weight: 600;">
                                                        Repository Audit
                                                    </div>
                                                    <div style="font-size: 18px; font-weight: 700; color: #000000; font-family: 'JetBrains Mono', monospace; word-break: break-all;">
                                                        {safe_repo}
                                                    </div>
                                                </td>
                                                <td align="right" valign="top" style="padding-left: 12px;">
                                                    <span style="display: inline-block; background-color: #e6f9f0; color: #059669; border: 1px solid #a7f3d0; font-size: 11px; font-weight: 600; font-family: 'JetBrains Mono', monospace; padding: 4px 12px; border-radius: 9999px; white-space: nowrap;">
                                                        ● COMPLETED
                                                    </span>
                                                </td>
                                            </tr>
                                        </table>
                                        <div style="margin-top: 12px; font-size: 13px; line-height: 1.5; color: #555555;">
                                            Automated code analysis, CI/CD pipeline diagnosis, and container deployment blueprint have been generated.
                                        </div>
                                    </td>
                                </tr>

                                <!-- Partition 2: Dimensions & Spec Columns (Divided by Vertical Partition) -->
                                <tr>
                                    <td style="padding: 0; border-bottom: 1px solid #eeeeea;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <!-- Left Col: Key Features -->
                                                <td width="50%" valign="top" style="padding: 20px 24px; border-right: 1px solid #eeeeea;">
                                                    <div style="font-size: 11px; font-family: 'JetBrains Mono', monospace; text-transform: uppercase; letter-spacing: 0.8px; color: #777777; margin-bottom: 12px; font-weight: 600;">
                                                        Included Capabilities
                                                    </div>
                                                    <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">
                                                        <tr>
                                                            <td style="padding: 3px 0; font-size: 12px; color: #222222;">
                                                                <span style="display: inline-block; width: 6px; height: 6px; background-color: #000000; border-radius: 50%; margin-right: 8px; vertical-align: middle;"></span>
                                                                Zero-Config CI/CD Generation
                                                            </td>
                                                        </tr>
                                                        <tr>
                                                            <td style="padding: 3px 0; font-size: 12px; color: #222222;">
                                                                <span style="display: inline-block; width: 6px; height: 6px; background-color: #000000; border-radius: 50%; margin-right: 8px; vertical-align: middle;"></span>
                                                                1-Click Deploy (Render, Pages)
                                                            </td>
                                                        </tr>
                                                        <tr>
                                                            <td style="padding: 3px 0; font-size: 12px; color: #222222;">
                                                                <span style="display: inline-block; width: 6px; height: 6px; background-color: #000000; border-radius: 50%; margin-right: 8px; vertical-align: middle;"></span>
                                                                Intelligent Hosting &amp; Routing Bot
                                                            </td>
                                                        </tr>
                                                        <tr>
                                                            <td style="padding: 3px 0; font-size: 12px; color: #222222;">
                                                                <span style="display: inline-block; width: 6px; height: 6px; background-color: #000000; border-radius: 50%; margin-right: 8px; vertical-align: middle;"></span>
                                                                End-to-End Secure Pipeline
                                                            </td>
                                                        </tr>
                                                    </table>
                                                </td>

                                                <!-- Right Col: Spec -->
                                                <td width="50%" valign="top" style="padding: 20px 24px;">
                                                    <div style="font-size: 11px; font-family: 'JetBrains Mono', monospace; text-transform: uppercase; letter-spacing: 0.8px; color: #777777; margin-bottom: 10px; font-weight: 600;">
                                                        Execution Spec
                                                    </div>
                                                    <div style="font-size: 10px; font-family: 'JetBrains Mono', monospace; text-transform: uppercase; letter-spacing: 0.5px; color: #888888; margin-bottom: 2px; font-weight: 600;">AGENT TYPE</div>
                                                    <div style="font-size: 12px; font-weight: 700; color: #000000; font-family: 'JetBrains Mono', monospace; margin-bottom: 8px;">DeployBridge Auto-Bot</div>
                                                    
                                                    <div style="font-size: 10px; font-family: 'JetBrains Mono', monospace; text-transform: uppercase; letter-spacing: 0.5px; color: #888888; margin-bottom: 2px; font-weight: 600;">EXECUTION TIME</div>
                                                    <div style="font-size: 12px; font-weight: 700; color: #000000; font-family: 'JetBrains Mono', monospace;">{duration_str}</div>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>

                                <!-- Partition 3: PDF Attachment Strip -->
                                <tr>
                                    <td style="padding: 14px 24px; background-color: #fafaf8;">
                                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td width="22" valign="middle" align="center" style="font-size: 15px;">
                                                    📎
                                                </td>
                                                <td style="padding-left: 8px;" valign="middle">
                                                    <span style="font-size: 12px; font-weight: 600; color: #000000; font-family: 'JetBrains Mono', monospace;">
                                                        {safe_repo.replace('/', '_')}_analysis.pdf
                                                    </span>
                                                    <span style="font-size: 11px; color: #777777; margin-left: 6px;">(Attached)</span>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>

                            </table>
                        </td>
                    </tr>

                    <!-- Action Capsule Bento Box (Dashboard 54% + Docs 32% + GitHub Repo 14%) -->
                    <tr>
                        <td align="center" style="padding: 24px 4px 16px 4px;">
                            <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="width: 100%; max-width: 440px; margin: 0 auto; border: 1.5px solid #000000; border-radius: 9999px; overflow: hidden; background-color: #ffffff; border-collapse: separate; border-spacing: 0; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);">
                                <tr>
                                    <!-- Partition 1: Dashboard (54%) -->
                                    <td width="54%" style="background-color: #000000; border-radius: 9999px 0 0 9999px; text-align: center; vertical-align: middle; padding: 0;">
                                        <a href="{safe_dashboard}" target="_blank" style="display: block; width: 100%; padding: 11px 14px; background-color: #000000; color: #ffffff; text-decoration: none; font-size: 13px; font-weight: 700; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; text-align: center; white-space: nowrap; border-radius: 9999px 0 0 9999px; box-sizing: border-box;">
                                            Open in Dashboard &rarr;
                                        </a>
                                    </td>
                                    <!-- Partition 2: Docs (32%) -->
                                    <td width="32%" style="background-color: #ffffff; border-left: 1px solid #e0e0d8; text-align: center; vertical-align: middle; padding: 0;">
                                        <a href="{safe_docs}" target="_blank" style="display: block; width: 100%; padding: 11px 10px; background-color: #ffffff; color: #000000; text-decoration: none; font-size: 13px; font-weight: 600; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; text-align: center; white-space: nowrap; box-sizing: border-box;">
                                            Documentation ↗
                                        </a>
                                    </td>
                                    <!-- Partition 3: GitHub Repo Link (14%) -->
                                    <td width="14%" style="background-color: #ffffff; border-left: 1px solid #e0e0d8; border-radius: 0 9999px 9999px 0; text-align: center; vertical-align: middle; padding: 0;">
                                        <a href="{safe_github}" target="_blank" title="View GitHub Repository" style="display: block; width: 100%; padding: 10px 0; background-color: #ffffff; text-align: center; line-height: 1; border-radius: 0 9999px 9999px 0; box-sizing: border-box;">
                                            <img src="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png" width="18" height="18" alt="GitHub Repo" style="display: inline-block; vertical-align: middle; border: 0; width: 18px; height: 18px;" />
                                        </a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Subfooter -->
                    <tr>
                        <td align="center" style="padding: 12px 16px 0 16px; font-size: 11px; font-family: 'JetBrains Mono', monospace; color: #888888; line-height: 1.6;">
                            <div>DEPLOYBRIDGE CLOUD &bull; SECURE AGENT &bull; {timestamp_str}</div>
                            <div style="margin-top: 4px; color: #666666;">
                                Triggered automatically for <strong>{safe_repo}</strong>.
                            </div>
                        </td>
                    </tr>

                </table>
                <!-- /Center Column -->

            </td>
        </tr>
    </table>

</body>
</html>
"""


def get_email_plain_template(
    repo_name: str,
    dashboard_link: str,
    report_url: str | None = None,
    model_used: str | None = None,
    docs_link: str = "https://deploybridge.com/docs",
) -> str:
    """Fallback plain text template for clients that do not support HTML rendering."""
    lines = [
        f"DEPLOYBRIDGE REPORT: {repo_name}",
        "=" * 48,
        "",
        f"Repository audit for '{repo_name}' is complete.",
        "",
        "INCLUDED CAPABILITIES:",
        "- Zero-Config CI/CD Generation",
        "- 1-Click Deploy (Render, Pages)",
        "- Intelligent Hosting & Routing Bot",
        "- End-to-End Secure Pipeline",
        "",
        f"View in Dashboard: {dashboard_link}",
        f"Documentation: {docs_link}",
    ]
    if report_url:
        lines.append(f"Cloud PDF: {report_url}")

    lines.extend([
        "",
        "--",
        "DeployBridge Cloud",
    ])
    return "\n".join(lines)


class EmailService:
    @staticmethod
    def send_report_email(
        to_email: str,
        repo_name: str,
        pdf_bytes: bytes | None,
        dashboard_link: str = "https://deploybridge.com/dashboard/reports",
        report_url: str | None = None,
        model_used: str | None = None,
        duration_ms: int | None = None,
        docs_link: str = "https://deploybridge.com/docs",
    ) -> bool:
        """
        Send a beautifully styled multipart (HTML + Plain + PDF attachment) email.
        Returns True if successful, False if email delivery is disabled or failed.
        """
        if not getattr(settings, "REPORT_DELIVERY_ENABLED", False):
            logger.info("Report delivery is disabled via REPORT_DELIVERY_ENABLED")
            return False

        try:
            smtp_host = getattr(settings, "SMTP_HOST", None)
            smtp_port = getattr(settings, "SMTP_PORT", 587)
            smtp_user = getattr(settings, "SMTP_USER", None)
            smtp_pass = getattr(settings, "SMTP_PASSWORD", None)
            smtp_from = getattr(settings, "SMTP_FROM", None)

            if not all([smtp_host, smtp_user, smtp_pass, smtp_from]):
                logger.warning("SMTP configuration is incomplete, cannot send email")
                return False

            # Outer multipart/mixed message to hold alternative body + attachments
            msg = MIMEMultipart("mixed")
            msg["From"] = f"DeployBridge <{smtp_from}>"
            msg["To"] = to_email
            msg["Subject"] = f"⚡ DeployBridge Report: {repo_name}"

            # Inner multipart/alternative message for plain text and HTML
            msg_alternative = MIMEMultipart("alternative")

            # 1. Plain text version
            plain_body = get_email_plain_template(
                repo_name=repo_name,
                dashboard_link=dashboard_link,
                report_url=report_url,
                model_used=model_used,
                docs_link=docs_link,
            )
            msg_alternative.attach(MIMEText(plain_body, "plain", "utf-8"))

            # 2. Rich HTML Bento-box version (Light Theme)
            html_body = get_email_html_template(
                repo_name=repo_name,
                dashboard_link=dashboard_link,
                report_url=report_url,
                model_used=model_used,
                duration_ms=duration_ms,
                docs_link=docs_link,
            )
            msg_alternative.attach(MIMEText(html_body, "html", "utf-8"))

            # Attach the alternative part to the mixed outer message
            msg.attach(msg_alternative)

            # 3. Attach PDF if provided
            if pdf_bytes:
                clean_filename = f"{repo_name.replace('/', '_')}_analysis.pdf"
                part = MIMEApplication(pdf_bytes, Name=clean_filename)
                part["Content-Disposition"] = f'attachment; filename="{clean_filename}"'
                msg.attach(part)

            # Send via SMTP
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)

            logger.info(f"Email sent successfully to {to_email} for {repo_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return False
