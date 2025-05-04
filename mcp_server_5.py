from mcp.server.fastmcp import FastMCP, Context
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from typing import List, Dict, Any
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class EmailManager:
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = os.getenv("EMAIL_USER")
        self.sender_password = os.getenv("EMAIL_PASSWORD")
        
        # Validate credentials
        if not self.sender_email or not self.sender_password:
            raise ValueError("Email credentials not found in environment variables")
        
        print(f"Email server configured with: {self.sender_email}")

    def send_email(self, recipient_email: str, subject: str, body: str) -> bool:
        """
        Send an email using SMTP.
        
        Args:
            recipient_email: Email address of the recipient
            subject: Email subject
            body: Email body content
        """
        try:
            print(f"Attempting to send email to {recipient_email}")
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = recipient_email
            msg['Subject'] = subject

            # Add body
            msg.attach(MIMEText(body, 'html'))

            print("Connecting to SMTP server...")
            # Create SMTP session
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                print("Starting TLS...")
                server.starttls()
                print("Logging in...")
                server.login(self.sender_email, self.sender_password)
                print("Sending message...")
                server.send_message(msg)
                print("Message sent successfully!")
            
            return True
        except smtplib.SMTPAuthenticationError as e:
            print(f"SMTP Authentication Error: {str(e)}")
            return False
        except smtplib.SMTPException as e:
            print(f"SMTP Error: {str(e)}")
            return False
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return False

# Initialize FastMCP server
mcp = FastMCP("email")
email_manager = EmailManager()

@mcp.tool()
async def send_sheet_email(
    recipient_email: str,
    spreadsheet_id: str,
    search_query: str,
    ctx: Context
) -> str:
    """
    Send an email with a link to the Google Sheet containing search results.
    
    Args:
        recipient_email: Email address of the recipient
        spreadsheet_id: The ID of the Google Sheet
        search_query: The original search query
        ctx: MCP context for logging
    """
    try:
        # Create the Google Sheet URL
        sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
        
        # Create email content
        subject = f"Search Results for: {search_query}"
        body = f"""
        <html>
            <body>
                <h2>Search Results</h2>
                <p>Here are the search results for your query: <strong>{search_query}</strong></p>
                <p>You can view the complete results in the Google Sheet:</p>
                <p><a href="{sheet_url}">Open Google Sheet</a></p>
                <p>Timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            </body>
        </html>
        """

        # Send the email
        success = email_manager.send_email(recipient_email, subject, body)
        
        if success:
            await ctx.info(f"Successfully sent email to {recipient_email}")
            return "Email has been sent successfully with the Google Sheet link."
        else:
            await ctx.error("Failed to send email")
            return "Error: Failed to send email with Google Sheet link. Check the logs for details."
        
    except Exception as e:
        await ctx.error(f"Error sending email: {str(e)}")
        return f"Error: Failed to send email. {str(e)}"

if __name__ == "__main__":
    print("mcp_server_5.py starting")
    mcp.run(transport="stdio")