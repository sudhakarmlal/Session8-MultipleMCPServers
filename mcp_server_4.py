from mcp.server.fastmcp import FastMCP, Context
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os.path
import pickle
from typing import List, Dict, Any
import json
from datetime import datetime

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

class GoogleSheetsManager:
    def __init__(self):
        self.creds = None
        self.service = None
        self._initialize_credentials()

    def _initialize_credentials(self):
        """Initialize Google Sheets credentials."""
        # The file token.pickle stores the user's access and refresh tokens
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                self.creds = pickle.load(token)
        
        # If there are no (valid) credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                self.creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(self.creds, token)

        self.service = build('sheets', 'v4', credentials=self.creds)

    def append_to_sheet(self, spreadsheet_id: str, range_name: str, values: List[List[Any]]) -> Dict:
        """Append values to a Google Sheet."""
        body = {
            'values': values
        }
        result = self.service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()
        return result

# Initialize FastMCP server
mcp = FastMCP("google-sheets")
sheets_manager = GoogleSheetsManager()

@mcp.tool()
async def append_search_results(
    spreadsheet_id: str,
    range_name: str,
    search_query: str,
    search_results: str,
    ctx: Context
) -> str:
    """
    Append search results to a Google Sheet.
    
    Args:
        spreadsheet_id: The ID of the Google Sheet
        range_name: The range in A1 notation (e.g., 'Sheet1!A1')
        search_query: The original search query
        search_results: The formatted search results
        ctx: MCP context for logging
    """
    try:
        # Prepare the data to append
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        values = [[timestamp, search_query, search_results]]
        
        # Append to the sheet
        result = sheets_manager.append_to_sheet(spreadsheet_id, range_name, values)
        
        await ctx.info(f"Successfully appended search results to Google Sheet")
        return "Search results have been successfully added to the Google Sheet."
        
    except Exception as e:
        await ctx.error(f"Error appending to Google Sheet: {str(e)}")
        return f"Error: Failed to append search results to Google Sheet. {str(e)}"

if __name__ == "__main__":
    print("mcp_server_4.py starting")
    mcp.run(transport="stdio") 