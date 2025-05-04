# agent.py

import asyncio
import yaml
from core.loop import AgentLoop
from core.session import MultiMCP
import os
from dotenv import load_dotenv

def log(stage: str, msg: str):
    """Simple timestamped console logger."""
    import datetime
    now = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] [{stage}] {msg}")


async def main():
    # Load environment variables
    load_dotenv()
    
    print("🧠 Cortex-R Agent Ready")
    user_input = input("🧑 What do you want to solve today? → ")

    # Load MCP server configs from profiles.yaml
    with open("config/profiles.yaml", "r") as f:
        profile = yaml.safe_load(f)
        mcp_servers = profile.get("mcp_servers", [])

    # Add Google Sheets MCP server configuration
    google_sheets_config = {
        "name": "google-sheets",
        "script": "mcp_server_4.py",
        "transport": "stdio"
    }
    mcp_servers.append(google_sheets_config)

    # Add Email MCP server configuration
    email_config = {
        "name": "email",
        "script": "mcp_server_5.py",
        "transport": "stdio"
    }
    mcp_servers.append(email_config)

    # Add Telegram MCP server configuration with SSE transport
    telegram_config = {
        "name": "telegram",
        "script": "mcp_server_6.py",
        "transport": "sse",
        "url": "http://localhost:8000",  # SSE server URL
        "endpoints": {
            "send_question": "/send_question",
            "send_acknowledgement": "/send_acknowledgement",
            "events": "/events"  # SSE events endpoint
        }
    }
    mcp_servers.append(telegram_config)

    multi_mcp = MultiMCP(server_configs=mcp_servers)
    print("Agent before initialize")
    await multi_mcp.initialize()

    # Step 1: Send question to Telegram and get response
    log("telegram", "Sending question to Telegram...")
    try:
        telegram_response = await multi_mcp.call_tool(
            "send_question",
            {
                "question": user_input
            }
        )
        log("telegram", f"Telegram response: {telegram_response}")
    except Exception as e:
        log("error", f"Failed to send question to Telegram: {e}")
        telegram_response = None

    agent = AgentLoop(
        user_input=user_input,
        dispatcher=multi_mcp
    )

    try:
        # Step 2: Get final response from agent
        final_response = await agent.run()
        log("agent", f"Final response received: {final_response}")
        
        if final_response:
            # Step 3: Append to Google Sheet
            spreadsheet_id = "1_LD9iGSn-kSbcCcIUdYIY5XbQLXqJ_X40DJJFpHmq_c"
            range_name = "Sheet1!A1"

            try:
                sheet_result = await multi_mcp.call_tool(
                    "append_search_results",
                    {
                        "spreadsheet_id": spreadsheet_id,
                        "range_name": range_name,
                        "search_query": user_input,
                        "search_results": final_response
                    }
                )
                log("sheets", f"Google Sheets result: {sheet_result}")

                # Step 4: Send email with Google Sheet link
                recipient_email = "sudhakar272@gmail.com"
                try:
                    email_result = await multi_mcp.call_tool(
                        "send_sheet_email",
                        {
                            "recipient_email": recipient_email,
                            "spreadsheet_id": spreadsheet_id,
                            "search_query": user_input
                        }
                    )
                    log("email", f"Email result: {email_result}")

                    # Step 5: Send acknowledgement to Telegram
                    ack_message = f"✅ Email has been successfully sent to '{recipient_email}'"
                    try:
                        ack_result = await multi_mcp.call_tool(
                            "send_acknowledgement",
                            {
                                "message": ack_message
                            }
                        )
                        log("telegram", f"Acknowledgement result: {ack_result}")
                    except Exception as e:
                        log("error", f"Failed to send Telegram acknowledgement: {e}")
                except Exception as e:
                    log("error", f"Failed to send email: {e}")
            except Exception as e:
                log("error", f"Failed to update Google Sheet: {e}")
        
        print("\n💡 Final Answer:\n", final_response.replace("FINAL_ANSWER:", "").strip())

    except Exception as e:
        log("fatal", f"Agent failed: {e}")
        raise
    finally:
        # Clean up SSE clients
        await multi_mcp.shutdown()


if __name__ == "__main__":
    asyncio.run(main())


# Find the ASCII values of characters in INDIA and then return sum of exponentials of those values.
# How much Anmol singh paid for his DLF apartment via Capbridge? 
# What do you know about Don Tapscott and Anthony Williams?
# What is the relationship between Gensol and Go-Auto?
# which course are we teaching on Canvas LMS?
# Summarize this page: https://theschoolof.ai/
# What is the log value of the amount that Anmol singh paid for his DLF apartment via Capbridge? 